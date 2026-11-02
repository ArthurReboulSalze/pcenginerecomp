"""Bounded persistent client for the optional loopback development server.

Only game-owned guest/SDL render targets are available, never the host desktop.
Keep a DevClient context open while holding input; disconnect releases its mask.
Uses only Python's standard library and writes captures with exclusive creation.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import math
from pathlib import Path
import socket
import struct
import sys
import threading
import time
import zlib

try:
    from scripts.dev_journal import JournalError, WireJournal
except ModuleNotFoundError:  # Direct invocation from scripts/.
    from dev_journal import JournalError, WireJournal

MAX_REQUEST = 8192
MAX_RESPONSE = 17 * 1024 * 1024
MAX_PIXELS = 4_000_000
MAX_TOKEN = (1 << 53) - 1
MAX_COUNTER = (1 << 64) - 1


class DevError(RuntimeError):
    """A rejected command or invalid development-server response."""


class ProtocolError(DevError):
    """A failed request whose connection closes before control returns."""


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")
    return value


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response field")
        result[key] = value
    return result


def _constant(_):
    raise ValueError("non-finite JSON number")


def _finite_float(value):
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('non-finite JSON number')
    return result


def _geometry(width, height, source="present"):
    _integer(width, 1, MAX_PIXELS, "width")
    _integer(height, 1, MAX_PIXELS, "height")
    if width * height > MAX_PIXELS:
        raise ValueError("capture exceeds four-million-pixel limit")
    if source == "guest" and (width > 1024 or height > 512):
        raise ValueError("guest capture geometry out of range")
    return width * height * 3


def _execution_policy(value):
    """Validate opt-in host policy metadata without importing a guest SDK."""
    fields = {'schema', 'reference_enabled', 'selected', 'configured_tier',
              'effective_policy', 'effective_native_span'}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError('unexpected execution policy fields')
    if type(value['schema']) is not int or value['schema'] != 1:
        raise ValueError('unsupported execution policy schema')
    if type(value['reference_enabled']) is not bool or value['reference_enabled'] is not True:
        raise ValueError('execution policy requires enabled reference capability')
    if type(value['selected']) is not bool:
        raise ValueError('execution policy selected must be boolean')
    tier = value['configured_tier']
    if tier not in ('native', 'hybrid'):
        raise ValueError('invalid configured execution tier')
    if value['effective_policy'] != ('interpreter' if value['selected'] else tier):
        raise ValueError('execution policy disagrees with selection')
    span = _integer(value['effective_native_span'], 0, 256, 'effective native span')
    if (value['selected'] and span != 0) or (not value['selected'] and span == 0):
        raise ValueError('execution policy span disagrees with selection')
    return value


def _capture_view(value, *, page=None):
    """Validate code-free retired-source evidence, including loss accounting."""
    if not isinstance(value, dict):
        raise ValueError("capture response requires an object")
    if type(value.get("schema")) is not int or value["schema"] != 1:
        raise ValueError("unsupported live capture schema")
    _integer(value.get("runtime_abi"), 1, (1 << 32) - 1, "runtime ABI")
    if type(value.get("enabled")) is not bool:
        raise ValueError("capture enabled must be boolean")
    base = {"schema", "runtime_abi", "enabled"}
    if not value["enabled"]:
        if set(value) != base or page is not None:
            raise ValueError("disabled capture has no source history")
        return value
    counters = {"retired_instructions", "native_instructions", "interpreted_instructions",
                "retained_native_instructions", "retained_interpreted_instructions",
                "dropped_instructions", "unreadable_instructions"}
    fields = base | counters | {"capacity", "identity_count", "complete", "window"}
    if 'checkpoint_origin' in value:
        fields.add('checkpoint_origin')
    if 'execution_policy' in value:
        fields.add('execution_policy')
    if page is not None:
        fields |= {"offset", "limit", "next_offset", "done", "sources"}
    if set(value) != fields:
        raise ValueError("unexpected live capture fields")
    policy = None
    if 'execution_policy' in value:
        policy = _execution_policy(value['execution_policy'])
        if value['runtime_abi'] < 29:
            raise ValueError('capture execution policy requires ABI29 or later')
    for key in counters:
        _integer(value[key], 0, MAX_COUNTER, key)
    _integer(value["capacity"], 1, 65536, "capture capacity")
    _integer(value["identity_count"], 0, value["capacity"], "identity count")
    native, interpreted = value["native_instructions"], value["interpreted_instructions"]
    if policy and policy['selected'] and native:
        raise ValueError('interpreter reference capture contains native retirements')
    retained_native = value["retained_native_instructions"]
    retained_interpreted = value["retained_interpreted_instructions"]
    retained = retained_native + retained_interpreted
    losses = value["dropped_instructions"] + value["unreadable_instructions"]
    if (native + interpreted != value["retired_instructions"] or
            retained + losses != value["retired_instructions"] or
            retained_native > native or retained_interpreted > interpreted or
            value["identity_count"] > retained or
            (value["identity_count"] == 0 and retained != 0)):
        raise ValueError("capture retirement/loss accounting does not conserve")
    if type(value["complete"]) is not bool or value["complete"] != (losses == 0):
        raise ValueError("capture completeness differs from loss counters")
    window = value["window"]
    common = {"requested_start_frame", "started", "current_frame", "current_ticks",
              "current_native_steps", "current_interpreter_steps"}
    started = {"actual_start_frame", "actual_start_ticks", "native_steps_before",
               "interpreter_steps_before"}
    if not isinstance(window, dict) or type(window.get("started")) is not bool:
        raise ValueError("capture window requires boolean started")
    if set(window) != common | (started if window["started"] else set()):
        raise ValueError("unexpected capture window fields")
    for key in set(window) - {"started"}:
        _integer(window[key], 0, MAX_COUNTER, key)
    if window["started"]:
        if not (window["requested_start_frame"] <= window["actual_start_frame"] <= window["current_frame"]
                and window["actual_start_ticks"] <= window["current_ticks"]
                and window["current_native_steps"] - window["native_steps_before"] == native
                and window["current_interpreter_steps"] - window["interpreter_steps_before"] == interpreted):
            raise ValueError("capture window differs from actual execution totals")
    elif value["retired_instructions"]:
        raise ValueError("unstarted capture has retired work")
    if 'checkpoint_origin' in value:
        origin = value['checkpoint_origin']
        if not isinstance(origin, dict) or set(origin) != {
                'sha256', 'ticks', 'frame', 'native_steps', 'interpreter_steps'}:
            raise ValueError('unexpected checkpoint capture origin fields')
        digest = origin['sha256']
        if (not isinstance(digest, str) or len(digest) != 64
                or any(c not in '0123456789abcdef' for c in digest)):
            raise ValueError('checkpoint capture origin requires lowercase SHA256')
        for key, current, before in (
                ('ticks', 'current_ticks', 'actual_start_ticks'),
                ('frame', 'current_frame', 'actual_start_frame'),
                ('native_steps', 'current_native_steps', 'native_steps_before'),
                ('interpreter_steps', 'current_interpreter_steps', 'interpreter_steps_before')):
            _integer(origin[key], 0, MAX_COUNTER, 'checkpoint origin '+key)
            if origin[key] > window[current] or (window['started'] and origin[key] > window[before]):
                raise ValueError('checkpoint origin follows capture execution window')
    if page is not None:
        offset, limit, retired = page
        for key, expected in (("offset", offset), ("limit", limit), ("retired_instructions", retired)):
            if type(value[key]) is not int or value[key] != expected:
                raise ValueError("capture page differs from request")
        count = value["identity_count"]
        expected_next = min(offset + limit, count)
        if offset > count:
            raise ValueError("capture page starts beyond retained identities")
        if type(value["next_offset"]) is not int or value["next_offset"] != expected_next:
            raise ValueError("capture page has invalid next offset")
        if type(value["done"]) is not bool or value["done"] != (expected_next == count):
            raise ValueError("capture page has invalid terminal marker")
        rows = value["sources"]
        if not isinstance(rows, list) or len(rows) != expected_next - offset:
            raise ValueError("capture page has invalid source extent")
        for index, row in enumerate(rows, offset):
            if not isinstance(row, dict) or set(row) != {"source_id", "pc", "mpr", "physical", "native_hits", "interpreted_hits"}:
                raise ValueError("unexpected capture source fields")
            if type(row["source_id"]) is not int or row["source_id"] != index:
                raise ValueError("capture source ID differs from append index")
            _integer(row["pc"], 0, 65535, "logical PC")
            if not isinstance(row["mpr"], list) or len(row["mpr"]) != 8:
                raise ValueError("capture source requires all eight MPRs")
            for bank in row["mpr"]:
                _integer(bank, 0, 255, "MPR")
            if not isinstance(row["physical"], list) or not 1 <= len(row["physical"]) <= 7:
                raise ValueError("capture source requires 1..7 physical fetch addresses")
            for byte, address in enumerate(row["physical"]):
                _integer(address, 0, 0x1FFFFF, "physical source address")
                logical = (row["pc"] + byte) & 65535
                if address != (row["mpr"][logical >> 13] << 13) | (logical & 8191):
                    raise ValueError("capture physical source differs from PC/MPR mapping")
            for key in ("native_hits", "interpreted_hits"):
                _integer(row[key], 0, value["retained_" + key.replace("hits", "instructions")], key)
            if not row["native_hits"] + row["interpreted_hits"]:
                raise ValueError("capture source has no retirement hits")
        if (sum(row["native_hits"] for row in rows) > retained_native or
                sum(row["interpreted_hits"] for row in rows) > retained_interpreted):
            raise ValueError("capture page hits exceed retained totals")
    return value


class DevClient:
    """One persistent, request-serialized loopback connection.

    Protocol failures close the socket. A server command rejection keeps the
    connection open, allowing the caller to release input or inspect status.
    Each call has one total timeout, including fragmented response reads.
    ``journal`` optionally names a new private wire file. Raw replies are
    flushed/fsynced before admission; journaling errors close the connection.
    A synchronous OS fsync cannot be interrupted: a deadline overrun is refused
    after it returns, with no claim that an already sent command was undone.
    """

    def __init__(self, port, host="127.0.0.1", timeout=30.0, *, journal=None):
        _integer(port, 1, 65535, "port")
        if host == "localhost":
            host = "127.0.0.1"
        if not ipaddress.ip_address(host).is_loopback:
            raise ValueError("development client requires a loopback address")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 600:
            raise ValueError("timeout must be in (0,600] seconds")
        self.timeout = float(timeout)
        self._socket = None
        self._buffer = bytearray()
        self._next_id = 1
        self._lock = threading.Lock()
        # Refuse an existing/unwritable journal before contacting a host.
        self._journal = WireJournal(journal, host=host, port=port) if journal is not None else None
        try:
            self._socket = socket.create_connection((host, port), self.timeout)
        except OSError as error:
            try:
                if self._journal is not None:
                    self._journal.failure(0, error, phase='connect')
            finally:
                self.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        sock, self._socket = self._socket, None
        try:
            if sock is not None:
                sock.close()
        finally:
            self._buffer.clear()
            if self._journal is not None:
                self._journal.close()

    def call(self, cmd, **args):
        return self._request(cmd, args, self.timeout)

    def _request(self, cmd, args, timeout):
        if not isinstance(cmd, str) or not cmd.isascii() or not cmd or len(cmd) > 64:
            raise ValueError("command must contain 1..64 ASCII characters")
        if "id" in args or "cmd" in args:
            raise ValueError("reserved request field")
        with self._lock:
            if self._socket is None:
                raise DevError("development connection is closed")
            identity = self._next_id
            _integer(identity, 1, (1 << 53) - 1, "request ID")
            request = json.dumps({"id": identity, "cmd": cmd, **args}, ensure_ascii=True,
                                 separators=(",", ":"), allow_nan=False).encode("ascii") + b"\n"
            if len(request) > MAX_REQUEST:
                raise ValueError("request exceeds 8192-byte limit")
            self._next_id += 1
            deadline = time.monotonic() + timeout
            try:
                if self._journal is not None:
                    self._journal.wire('request', identity, request)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('development request timed out before send')
                self._socket.settimeout(remaining)
                self._socket.sendall(request)
                while True:
                    newline = self._buffer.find(b"\n")
                    if newline >= 0:
                        if newline + 1 > MAX_RESPONSE:
                            raise ValueError("response exceeds 17-MiB limit")
                        line = bytes(self._buffer[:newline])
                        del self._buffer[:newline + 1]
                        if self._journal is not None:
                            self._journal.wire('response', identity, line + b'\n')
                        break
                    if len(self._buffer) >= MAX_RESPONSE:
                        raise ValueError("response exceeds 17-MiB limit")
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise TimeoutError("development response timed out")
                    self._socket.settimeout(remaining)
                    block = self._socket.recv(min(65536, MAX_RESPONSE - len(self._buffer)))
                    if not block:
                        raise ValueError("development server disconnected before a complete response")
                    self._buffer.extend(block)
                response = json.loads(line.decode("utf-8"), object_pairs_hook=_object,
                                      parse_constant=_constant, parse_float=_finite_float)
                if not isinstance(response, dict) or type(response.get("id")) is not int or response["id"] != identity:
                    raise ValueError("response ID does not match request")
                if type(response.get("ok")) is not bool:
                    raise ValueError("response must contain boolean ok")
                if time.monotonic() > deadline:
                    raise TimeoutError('development response admission timed out')
            except JournalError as error:
                self.close()
                raise ProtocolError(str(error)) from error
            except (OSError, ValueError, RecursionError) as error:
                try:
                    if self._journal is not None:
                        self._journal.failure(identity, error, bytes(self._buffer))
                except JournalError as journal_error:
                    self.close()
                    raise ProtocolError(f'{error}; {journal_error}') from journal_error
                self.close()
                raise ProtocolError(str(error)) from error
            if not response["ok"]:
                message = response.get("error", "command rejected")
                raise DevError(message if isinstance(message, str) else "command rejected")
            return response

    def read_memory(self, address, length):
        """Read a bounded physical RAM/ROM range while the guest is paused."""
        _integer(address, 0, 0x1FFFFF, "physical address")
        _integer(length, 1, min(256, 0x200000-address), "memory length")
        response = self.call("read_memory", address=address, length=length)
        try:
            if type(response.get("address")) is not int or response["address"] != address \
                    or type(response.get("length")) is not int or response["length"] != length:
                raise ValueError("memory response range differs from request")
            data = response.get("data")
            if not isinstance(data, str) or len(data) != length*2 \
                    or any(c not in "0123456789abcdef" for c in data):
                raise ValueError("invalid memory response hex")
            return bytes.fromhex(data)
        except ValueError as error:
            self.close()
            raise ProtocolError(str(error)) from error

    def write_memory(self, address, data, expected):
        """Compare and edit physical RAM; requires explicit host write opt-in."""
        _integer(address, 0, 0x1FFFFF, "physical address")
        if not isinstance(data, bytes) or not isinstance(expected, bytes) \
                or not 1 <= len(data) <= min(256, 0x200000-address) \
                or len(data) != len(expected):
            raise ValueError("memory data and expected must be equal bounded byte strings")
        response = self.call("write_memory", address=address, data=data.hex(), expected=expected.hex())
        if type(response.get("address")) is not int or response["address"] != address \
                or type(response.get("length")) is not int or response["length"] != len(data):
            self.close()
            raise ProtocolError("memory write acknowledgement differs from request")
        return response

    def capture(self, source="guest"):
        if source not in ("guest", "present"):
            raise ValueError("capture source must be guest or present")
        response = self.call("screenshot", source=source)
        try:
            if response.get("source") != source:
                raise ValueError("capture source does not match request")
            if response.get("encoding") != "rgb24-base64":
                raise ValueError("unsupported capture encoding")
            expected = _geometry(response.get("width"), response.get("height"), source)
            _integer(response.get("frame"), 0, (1 << 64) - 1, "frame")
            _integer(response.get("ticks"), 0, (1 << 64) - 1, "ticks")
            _integer(response.get("frame_ticks"), 0, response["ticks"], "frame ticks")
            data = response.get("data")
            if not isinstance(data, str) or len(data) != ((expected + 2) // 3) * 4:
                raise ValueError("capture base64 extent differs from geometry")
            rgb = base64.b64decode(data, validate=True)
            if len(rgb) != expected:
                raise ValueError("capture RGB extent differs from geometry")
        except (ValueError, binascii.Error) as error:
            self.close()
            raise ProtocolError(str(error)) from error
        metadata = {key: response[key] for key in ("width", "height", "frame", "ticks", "frame_ticks", "source")}
        return metadata, rgb

    def capture_summary(self):
        """Inspect the accumulated capture at a settled pause without flushing it."""
        response = self.call("capture_summary")
        try:
            return _capture_view(response.get("capture"))
        except ValueError as error:
            self.close()
            raise ProtocolError(str(error)) from error

    def capture_sources(self, offset, limit, retired):
        """Read one bounded page; retired binds it to a capture-summary epoch."""
        _integer(offset, 0, 65536, "source offset")
        _integer(limit, 1, 256, "source limit")
        _integer(retired, 0, MAX_TOKEN, "capture retirement token")
        response = self.call("capture_sources", offset=offset, limit=limit, retired=retired)
        try:
            return _capture_view(response.get("capture"), page=(offset, limit, retired))
        except ValueError as error:
            self.close()
            raise ProtocolError(str(error)) from error

    def capture_history(self):
        """Collect all retained rows at one epoch, preserving explicit loss/window data.

        This is a bounded set of pre-retirement encoded source spans, not a
        chronological trace or a bus-read log. Completeness only covers the
        stated capture window. Callers must account for physical backing aliases.
        """
        summary = self.capture_summary()
        if not summary["enabled"]:
            raise DevError("code capture disabled")
        _integer(summary["retired_instructions"], 0, MAX_TOKEN, "capture retirement token")
        rows = []
        while True:
            page = self.capture_sources(len(rows), 256, summary["retired_instructions"])
            metadata = {key: value for key, value in page.items()
                        if key not in {'offset', 'limit', 'next_offset', 'done', 'sources'}}
            if metadata != summary:
                self.close()
                raise ProtocolError("capture epoch changed during pagination")
            rows.extend(page["sources"])
            if page["done"]:
                break
        if (sum(row["native_hits"] for row in rows) != summary["retained_native_instructions"] or
                sum(row["interpreted_hits"] for row in rows) != summary["retained_interpreted_instructions"]):
            self.close()
            raise ProtocolError("full capture history differs from retained totals")
        return {**summary, "sources": rows}

    def advance(self, frames, *, reference=False):
        """Advance a paused simulation to its bounded target; reference is opt-in.

        Reference execution requires the enabled same-build host capability and
        its pre-dispatch policy latch. This never sends an unbounded resume.
        """
        _integer(frames, 1, 600, "frames")
        if type(reference) is not bool:
            raise ValueError('reference must be boolean')
        deadline = time.monotonic() + self.timeout
        queued = self._request("reference_frames" if reference else "step_frames",
                               {"frames": frames}, self.timeout)
        try:
            target = _integer(queued.get("target_frame"), 0, (1 << 64) - 1, "target frame")
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise DevError("frame advancement timed out")
                status = self._request("status", {}, remaining)
                current = _integer(status.get("frame"), 0, (1 << 64) - 1, "frame")
                if type(status.get("paused")) is not bool:
                    raise ValueError("status must contain boolean paused")
                if reference:
                    host = status.get('host')
                    if not isinstance(host, dict):
                        raise ValueError('reference status requires host execution policy')
                    policy = _execution_policy(host.get('execution_policy'))
                    if not policy['selected']:
                        raise ValueError('reference advancement requires selected interpreter policy')
                if current >= target and status["paused"]:
                    return status
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        except ValueError as error:
            self.close()
            raise ProtocolError(str(error)) from error


def encode_png(width, height, rgb):
    expected = _geometry(width, height)
    if not isinstance(rgb, bytes) or len(rgb) != expected:
        raise ValueError("invalid RGB24 payload")

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    stride = width * 3
    rows = b"".join(b"\0" + rgb[start:start + stride] for start in range(0, len(rgb), stride))
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


def write_capture(path, metadata, rgb):
    """Write a user-selected new PNG/PPM directly, with no intermediate file."""
    path = Path(path)
    width, height = metadata["width"], metadata["height"]
    expected = _geometry(width, height)
    if not isinstance(rgb, bytes) or len(rgb) != expected:
        raise ValueError("invalid RGB24 payload")
    if path.suffix.lower() == ".png":
        data = encode_png(width, height, rgb)
    elif path.suffix.lower() == ".ppm":
        data = f"P6\n{width} {height}\n255\n".encode("ascii") + rgb
    else:
        raise ValueError("capture extension must be .png or .ppm")
    with path.open("xb") as stream:
        stream.write(data)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument("--wire-journal", type=Path,
                        help="new private JSONL file; fsync raw requests/replies before validation")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("ping", "status", "pause", "resume", "clear_input"):
        commands.add_parser(command)
    for command in ("capture-summary", "capture-history"):
        commands.add_parser(command)
    sources = commands.add_parser("capture-sources")
    sources.add_argument("offset", type=int)
    sources.add_argument("limit", type=int)
    sources.add_argument("--retired", type=int, required=True)
    shot = commands.add_parser("screenshot")
    shot.add_argument("output", type=Path)
    shot.add_argument("--source", choices=("guest", "present"), default="guest")
    frames = commands.add_parser("frames")
    frames.add_argument("count", type=int)
    frames.add_argument("--resume", action="store_true")
    reference_frames = commands.add_parser("reference-frames",
        help="bounded interpreter reference window on an explicitly enabled paused host")
    reference_frames.add_argument("count", type=int)
    inputs = commands.add_parser("input")
    inputs.add_argument("mask", type=lambda value: int(value, 0))
    inputs.add_argument("--slot", type=int, default=0)
    duration = inputs.add_mutually_exclusive_group(required=True)
    duration.add_argument("--frames", type=int)
    duration.add_argument("--seconds", type=float)
    inputs.add_argument("--resume", action="store_true")
    memory_read = commands.add_parser("read-memory")
    memory_read.add_argument("address", type=lambda value: int(value, 0))
    memory_read.add_argument("length", type=int)
    memory_write = commands.add_parser("write-memory")
    memory_write.add_argument("address", type=lambda value: int(value, 0))
    memory_write.add_argument("data", help="1..256 bytes as contiguous hex")
    memory_write.add_argument("--expected", required=True, help="current bytes as contiguous hex")
    args = parser.parse_args(argv)
    try:
        with DevClient(args.port, timeout=args.timeout, journal=args.wire_journal) as client:
            if args.command == "capture-summary":
                result = client.capture_summary()
            elif args.command == "capture-sources":
                result = client.capture_sources(args.offset, args.limit, args.retired)
            elif args.command == "capture-history":
                result = client.capture_history()
            elif args.command == "read-memory":
                data = client.read_memory(args.address, args.length)
                result = {"address": args.address, "length": len(data), "data": data.hex()}
            elif args.command == "write-memory":
                for value in (args.data, args.expected):
                    if not value or len(value) > 512 or len(value) % 2 or any(c not in "0123456789abcdefABCDEF" for c in value):
                        raise ValueError("memory bytes require 1..256 bytes of contiguous hex")
                result = client.write_memory(args.address, bytes.fromhex(args.data), bytes.fromhex(args.expected))
            elif args.command == "screenshot":
                metadata, rgb = client.capture(args.source)
                write_capture(args.output, metadata, rgb)
                result = {**metadata, "output": str(args.output)}
            elif args.command == "frames":
                client.call("pause")
                result = client.advance(args.count)
                if args.resume:
                    client.call("resume")
            elif args.command == "reference-frames":
                client.call("pause")
                result = client.advance(args.count, reference=True)
            elif args.command == "input":
                _integer(args.mask, 0, 0xFFF, "mask")
                _integer(args.slot, 0, 4, "slot")
                if args.frames is not None:
                    _integer(args.frames, 1, 600, "frames")
                    client.call("pause")
                elif not 0 < args.seconds <= 600:
                    raise ValueError("seconds must be in (0,600]")
                client.call("set_input", port=args.slot, mask=args.mask)
                try:
                    if args.frames is not None:
                        result = client.advance(args.frames)
                    else:
                        until = time.monotonic() + args.seconds
                        while time.monotonic() < until:
                            time.sleep(min(1, until - time.monotonic()))
                            client.call("ping")  # Preserve the server's bounded idle lease.
                        result = client.call("status")
                finally:
                    client.call("clear_input")
                if args.resume:
                    client.call("resume")
            else:
                result = client.call(args.command)
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (DevError, OSError, ValueError) as error:
        print(f"development client: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
