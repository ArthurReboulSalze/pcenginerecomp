"""Authored TCP development protocol, bounded image and output protection tests."""
import base64
import copy
import io
import json
from pathlib import Path
import socket
import struct
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import zlib

from scripts.dev_client import DevClient, DevError, ProtocolError, encode_png, main, write_capture


class Server:
    def __init__(self, handler):
        self.handler = handler
        self.requests = []
        self.errors = []
        self.socket = socket.socket()
        self.socket.bind(("127.0.0.1", 0))
        self.port = self.socket.getsockname()[1]
        self.socket.listen(1)
        self.socket.settimeout(2)
        self.thread = threading.Thread(target=self.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self.socket.close()
        self.thread.join(3)
        if self.thread.is_alive():
            raise AssertionError("authored server did not terminate")
        if self.errors:
            raise self.errors[0]

    def run(self):
        try:
            with self.socket.accept()[0] as connection:
                connection.settimeout(2)
                pending = bytearray()
                while True:
                    data = connection.recv(8192)
                    if not data:
                        return
                    pending.extend(data)
                    while b"\n" in pending:
                        line, _, rest = pending.partition(b"\n")
                        pending[:] = rest
                        request = json.loads(line)
                        self.requests.append(request)
                        response = self.handler(request)
                        if response is None:
                            return
                        if isinstance(response, dict):
                            response = json.dumps(response).encode() + b"\n"
                        fragments = response if isinstance(response, list) else [response]
                        for fragment in fragments:
                            connection.sendall(fragment)
        except ConnectionError:
            pass  # Expected when a bounded client rejects an authored bad reply.
        except Exception as error:
            self.errors.append(error)


def ok(request, **fields):
    return {"id": request["id"], "ok": True, **fields}


def capture(request, **changes):
    return ok(request, **{"source": request.get("source", "guest"), "encoding": "rgb24-base64",
                         "width": 2, "height": 1, "frame": 7, "ticks": 2500000,
                         "frame_ticks": 2400000,
                         "data": base64.b64encode(bytes((1, 2, 3, 253, 254, 255))).decode(), **changes})


def live_capture(*, rows=2, loss=0, started=True):
    # Two different internal byte variants may have identical visible spans.
    return {"schema": 1, "runtime_abi": 21, "enabled": True, "capacity": 512,
            "identity_count": rows, "retired_instructions": rows + loss,
            "native_instructions": rows, "interpreted_instructions": loss,
            "retained_native_instructions": rows, "retained_interpreted_instructions": 0,
            "dropped_instructions": loss, "unreadable_instructions": 0, "complete": not loss,
            "window": {"requested_start_frame": 3, "started": started, "current_frame": 5,
                       "current_ticks": 1000, "current_native_steps": 100 + rows,
                       "current_interpreter_steps": 30 + loss,
                       **({"actual_start_frame": 3, "actual_start_ticks": 600,
                           "native_steps_before": 100, "interpreter_steps_before": 30} if started else {})}}


def live_page(summary, request):
    offset, limit = request["offset"], request["limit"]
    end = min(summary["identity_count"], offset + limit)
    # Logical wrap and two different banks exercise each byte's translation.
    mapping = [7, 248, 2, 3, 4, 5, 6, 0]
    return {**copy.deepcopy(summary), "offset": offset, "limit": limit,
            "next_offset": end, "done": end == summary["identity_count"],
            "sources": [{"source_id": index, "pc": 65535, "mpr": mapping,
                         "physical": [8191, 7 * 8192], "native_hits": 1,
                         "interpreted_hits": 0} for index in range(offset, end)]}


def execution_policy(*, selected=True, tier='hybrid', span=16):
    return {'schema': 1, 'reference_enabled': True, 'selected': selected,
            'configured_tier': tier, 'effective_policy': 'interpreter' if selected else tier,
            'effective_native_span': 0 if selected else span}


def reference_capture(rows=2):
    summary = live_capture(rows=rows)
    summary.update(runtime_abi=29, native_instructions=0, interpreted_instructions=rows,
                   retained_native_instructions=0, retained_interpreted_instructions=rows,
                   execution_policy=execution_policy())
    summary['window'].update(current_native_steps=100, current_interpreter_steps=30+rows)
    summary['checkpoint_origin'] = {'sha256': 'a'*64, 'ticks': 500, 'frame': 2,
                                    'native_steps': 99, 'interpreter_steps': 29}
    return summary


def reference_page(summary, request):
    page = live_page(summary, request)
    for row in page['sources']:
        row.update(native_hits=0, interpreted_hits=1)
    return page


class LiveCaptureClientTests(unittest.TestCase):
    def test_reference_policy_preserves_imported_origin_and_paged_new_work(self):
        summary = reference_capture(rows=257)
        def respond(request):
            return ok(request, capture=summary if request['cmd'] == 'capture_summary'
                      else reference_page(summary, request))
        with Server(respond) as server, DevClient(server.port) as client:
            history = client.capture_history()
            self.assertEqual(history['execution_policy'], execution_policy())
            self.assertEqual(history['checkpoint_origin'], summary['checkpoint_origin'])
            self.assertEqual(history['window']['native_steps_before'], 100)
            self.assertEqual(history['native_instructions'], 0)
            self.assertEqual(history['interpreted_instructions'], 257)
            self.assertEqual(len(history['sources']), 257)
            self.assertTrue(all(r['native_hits'] == 0 and r['interpreted_hits'] == 1
                                for r in history['sources']))
        self.assertEqual([r.get('offset') for r in server.requests[1:]], [0, 256])

    def test_unselected_reference_capability_retains_configured_native_capture(self):
        for tier in ('native', 'hybrid'):
            summary = live_capture() | {'runtime_abi': 29,
                'execution_policy': execution_policy(selected=False, tier=tier, span=256)}
            def respond(request):
                return ok(request, capture=summary if request['cmd'] == 'capture_summary'
                          else live_page(summary, request))
            with self.subTest(tier=tier), Server(respond) as server, DevClient(server.port) as client:
                result = client.capture_history()
                self.assertEqual(result['execution_policy'], summary['execution_policy'])
                self.assertEqual(result['native_instructions'], 2)

    def test_reference_capture_rejects_untyped_or_incoherent_policy(self):
        invalid = [None, {}, execution_policy() | {'extra': 0}]
        for key, value in (('schema', True), ('schema', 2), ('reference_enabled', 1),
                           ('reference_enabled', False), ('selected', 1),
                           ('configured_tier', 'interpreter'), ('effective_policy', 'hybrid'),
                           ('effective_native_span', True), ('effective_native_span', 1),
                           ('effective_native_span', 0.0), ('effective_native_span', 257)):
            invalid.append(execution_policy() | {key: value})
        invalid.append(execution_policy(selected=False, span=0))
        for policy in invalid:
            summary = reference_capture() | {'execution_policy': policy}
            with self.subTest(policy=policy), Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_summary()
                with self.assertRaisesRegex(DevError, 'closed'):
                    client.call('ping')
        for changes in ({'runtime_abi': 28}, {'native_instructions': 1, 'interpreted_instructions': 1,
                'retained_native_instructions': 1, 'retained_interpreted_instructions': 1}):
            summary = reference_capture() | changes
            if 'native_instructions' in changes:
                summary['window'].update(current_native_steps=101, current_interpreter_steps=31)
            with self.subTest(changes=changes), Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_summary()

    def test_reference_policy_cannot_change_appear_or_disappear_between_pages(self):
        for drift in ('selected', 'tier', 'removed', 'inserted'):
            summary = reference_capture()
            if drift == 'inserted':
                summary.pop('execution_policy')
            def respond(request):
                if request['cmd'] == 'capture_summary':
                    return ok(request, capture=summary)
                page = reference_page(summary, request)
                if drift == 'removed':
                    page.pop('execution_policy')
                else:
                    page['execution_policy'] = execution_policy(
                        selected=drift != 'selected', tier='native' if drift == 'tier' else 'hybrid')
                return ok(request, capture=page)
            with self.subTest(drift=drift), Server(respond) as server, DevClient(server.port) as client:
                with self.assertRaisesRegex(ProtocolError, 'epoch changed'):
                    client.capture_history()

    def test_checkpoint_origin_survives_live_summary_pages_and_armed_windows(self):
        origin = {'sha256': 'a'*64, 'ticks': 500, 'frame': 2,
                  'native_steps': 99, 'interpreter_steps': 29}
        for started in (True, False):
            summary = live_capture(rows=2 if started else 0, started=started)
            summary['checkpoint_origin'] = origin
            def respond(request):
                return ok(request, capture=summary if request['cmd'] == 'capture_summary' else live_page(summary, request))
            with self.subTest(started=started), Server(respond) as server, DevClient(server.port) as client:
                self.assertEqual(client.capture_summary()['checkpoint_origin'], origin)
                history = client.capture_history()
                self.assertEqual(history['checkpoint_origin'], origin)
                self.assertEqual(history['retired_instructions'], 2 if started else 0)
                self.assertEqual(len(history['sources']), 2 if started else 0)

    def test_bad_checkpoint_capture_origins_close_connection(self):
        origin = {'sha256': 'a'*64, 'ticks': 500, 'frame': 2,
                  'native_steps': 99, 'interpreter_steps': 29}
        invalid = [None, {}, origin | {'extra': 1}, origin | {'sha256': 'A'*64},
                   origin | {'sha256': 'a'*63}, origin | {'ticks': True},
                   origin | {'frame': -1}, origin | {'native_steps': 2**64},
                   origin | {'interpreter_steps': 0.0}, origin | {'ticks': 1001},
                   origin | {'ticks': 700}, origin | {'frame': 6}, origin | {'frame': 4},
                   origin | {'native_steps': 103}, origin | {'native_steps': 101},
                   origin | {'interpreter_steps': 34}, origin | {'interpreter_steps': 31}]
        for item in invalid:
            summary = live_capture(loss=3);summary['checkpoint_origin'] = item
            with self.subTest(origin=item), Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_summary()
                with self.assertRaisesRegex(DevError, 'closed'):
                    client.call('ping')
        summary = live_capture(rows=0, started=False)
        summary['checkpoint_origin'] = origin | {'ticks': 1001}
        with Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
            with self.assertRaises(ProtocolError):
                client.capture_summary()

    def test_checkpoint_origin_cannot_change_appear_or_disappear_between_pages(self):
        origin = {'sha256': 'a'*64, 'ticks': 500, 'frame': 2,
                  'native_steps': 99, 'interpreter_steps': 29}
        for drift in ('changed', 'removed', 'inserted'):
            summary = live_capture()
            if drift != 'inserted':
                summary['checkpoint_origin'] = origin
            def respond(request):
                if request['cmd'] == 'capture_summary':
                    return ok(request, capture=summary)
                page = live_page(summary, request)
                if drift == 'removed':
                    page.pop('checkpoint_origin')
                else:
                    page['checkpoint_origin'] = origin | {'sha256': 'b'*64}
                return ok(request, capture=page)
            with self.subTest(drift=drift), Server(respond) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_history()
                with self.assertRaisesRegex(DevError, 'closed'):
                    client.call('ping')

    def test_pagination_conserves_hits_and_same_span_variants(self):
        summary = live_capture(rows=257, loss=3)
        def respond(request):
            return ok(request, capture=summary if request["cmd"] == "capture_summary" else live_page(summary, request))
        with Server(respond) as server, DevClient(server.port) as client:
            history = client.capture_history()
            self.assertEqual(history["sources"][0]["physical"], [8191, 57344])
            self.assertEqual(len(history["sources"]), 257)
            self.assertEqual(history["sources"][-1]["source_id"], 256)
            self.assertFalse(history["complete"])
            self.assertEqual(history["interpreted_instructions"], 3)
            self.assertEqual([r["cmd"] for r in server.requests], ["capture_summary", "capture_sources", "capture_sources"])
            self.assertEqual([r.get("offset") for r in server.requests[1:]], [0, 256])

    def test_empty_armed_window_and_disabled_capture_are_distinct(self):
        for summary in (live_capture(rows=0, started=False),
                        {"schema": 1, "runtime_abi": 21, "enabled": False}):
            with self.subTest(summary=summary), Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
                self.assertEqual(client.capture_summary(), summary)
                if not summary["enabled"]:
                    with self.assertRaisesRegex(DevError, "disabled"):
                        client.capture_history()
        summary = live_capture(rows=0)
        with Server(lambda r: ok(r, capture=summary if r["cmd"] == "capture_summary" else live_page(summary, r))) as server, DevClient(server.port) as client:
            self.assertEqual(client.capture_history()["sources"], [])

    def test_bad_summary_replies_close_connection(self):
        invalid = []
        for key, value in (("schema", True), ("runtime_abi", True), ("enabled", 1),
                           ("retired_instructions", True), ("identity_count", 3),
                           ("native_instructions", 1), ("retained_native_instructions", 1),
                           ("complete", False), ("dropped_instructions", 1),
                           ("capacity", 65537), ("extra", 0)):
            invalid.append({**live_capture(), key: value})
        for key, value in (("current_native_steps", 101), ("started", 1),
                           ("actual_start_ticks", 1001), ("native_steps_before", 103)):
            row = live_capture(); row["window"][key] = value; invalid.append(row)
        invalid.append({"schema": 1, "runtime_abi": 21, "enabled": False, "complete": True})
        invalid.append(None)
        for summary in invalid:
            with self.subTest(summary=summary), Server(lambda r: ok(r, capture=summary)) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_summary()
                with self.assertRaisesRegex(DevError, "closed"):
                    client.call("ping")

    def test_bad_pages_reject_stale_tokens_spans_and_injected_bytes(self):
        request = {"offset": 0, "limit": 1, "retired": 2}
        valid = live_page(live_capture(), request)
        invalid = []
        for key, value in (("retired_instructions", 1), ("offset", True), ("limit", 2),
                           ("next_offset", 2), ("done", True), ("sources", [])):
            invalid.append({**copy.deepcopy(valid), key: value})
        for key, value in (("source_id", True), ("pc", True), ("mpr", [0]),
                           ("physical", [8191, 0]), ("native_hits", 0),
                           ("interpreted_hits", 1), ("data", [169, 1])):
            page = copy.deepcopy(valid); page["sources"][0][key] = value; invalid.append(page)
        for page in invalid:
            with self.subTest(page=page), Server(lambda r: ok(r, capture=page)) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_sources(**request)

    def test_full_history_rejects_cross_page_drift_and_wrong_hit_totals(self):
        for drift in ("window", "hits"):
            summary = live_capture()
            def respond(request):
                if request["cmd"] == "capture_summary":
                    return ok(request, capture=summary)
                page = live_page(summary, request)
                if drift == "window":
                    page["window"]["current_ticks"] += 1
                else:
                    page["sources"][0]["native_hits"] = 2
                return ok(request, capture=page)
            with self.subTest(drift=drift), Server(respond) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.capture_history()

    def test_input_validation_precedes_network_and_rejection_is_recoverable(self):
        with Server(lambda r: {"id": r["id"], "ok": False, "error": "stale capture token"} if r["cmd"] == "capture_sources" else ok(r)) as server, DevClient(server.port) as client:
            for values in ((True, 1, 0), (0, True, 0), (0, 1, True),
                           (65537, 1, 0), (0, 257, 0), (0, 1, 1 << 53)):
                with self.assertRaises(ValueError):
                    client.capture_sources(*values)
            with self.assertRaisesRegex(DevError, "stale"):
                client.capture_sources(0, 1, 2)
            client.call("ping")
            self.assertEqual(len(server.requests), 2)

    def test_cli_history_and_summary_are_read_only_commands(self):
        summary = live_capture(rows=0)
        for command in ("capture-summary", "capture-history", "capture-sources"):
            with self.subTest(command=command), Server(lambda r: ok(r, capture=summary if r["cmd"] == "capture_summary" else live_page(summary, r))) as server, patch("sys.stdout", new_callable=io.StringIO) as output:
                args = ["--port", str(server.port), command]
                if command == "capture-sources":
                    args += ["0", "1", "--retired", "0"]
                self.assertEqual(main(args), 0)
                self.assertTrue(json.loads(output.getvalue())["complete"])
                self.assertTrue(all(r["cmd"] in ("capture_summary", "capture_sources") for r in server.requests))


class DevelopmentClientTests(unittest.TestCase):
    def test_memory_roundtrip_preserves_physical_range_and_expected_bytes(self):
        def respond(request):
            fields = {'address': request['address'], 'length': request.get('length', len(request.get('data', ''))//2)}
            if request['cmd'] == 'read_memory':
                fields['data'] = '01ff00'
            return ok(request, **fields)
        with Server(respond) as server:
            with DevClient(server.port) as client:
                self.assertEqual(client.read_memory(0x1F0000, 3), b'\x01\xff\0')
                client.write_memory(0x1F0000, b'\x02\x03\x04', b'\x01\xff\0')
            self.assertEqual(server.requests[1], {'id': 2, 'cmd': 'write_memory', 'address': 0x1F0000, 'data': '020304', 'expected': '01ff00'})

    def test_memory_bad_replies_close_connection(self):
        for changes in ({'address': 2}, {'address': True}, {'length': True}, {'length': 2},
                        {'data': 'zz'}, {'data': 'AA'}, {'data': 'a'}, {'data': 1}):
            with self.subTest(changes=changes), Server(lambda r, changes=changes: ok(r, **{'address': 1, 'length': 1, 'data': 'ab', **changes})) as server:
                with DevClient(server.port) as client:
                    with self.assertRaises(ProtocolError):
                        client.read_memory(1, 1)
                    with self.assertRaisesRegex(DevError, 'closed'):
                        client.call('ping')
        with Server(lambda r: ok(r, address=1, length=2)) as server:
            with DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.write_memory(1, b'\1', b'\0')

    def test_memory_argument_validation_precedes_network(self):
        with Server(lambda r: ok(r)) as server:
            with DevClient(server.port) as client:
                for address, length in ((True, 1), (-1, 1), (0x200000, 1), (1, 0), (1, 257), (0x1FFFFF, 2)):
                    with self.assertRaises(ValueError):
                        client.read_memory(address, length)
                for address, data, expected in ((1, b'', b''), (1, b'\0'*257, b'\0'*257),
                                                (1, b'\0', b''), (1, bytearray([0]), b'\0'),
                                                (0x1FFFFF, b'\0\0', b'\0\0')):
                    with self.assertRaises(ValueError):
                        client.write_memory(address, data, expected)
                client.call('ping')
            self.assertEqual(len(server.requests), 1)

    def test_persistent_serial_requests_fragmented_reply_and_ids(self):
        def respond(request):
            data = json.dumps(ok(request, command=request["cmd"])).encode() + b"\n"
            return [data[n:n+1] for n in range(len(data))]
        with Server(respond) as server:
            with DevClient(server.port) as client:
                self.assertEqual(client.call("set_input", port=0, mask=8)["id"], 1)
                self.assertEqual(client.call("ping")["id"], 2)
                self.assertEqual(client.call("clear_input")["id"], 3)
            self.assertEqual([r["cmd"] for r in server.requests], ["set_input", "ping", "clear_input"])

    def test_command_error_keeps_connection_usable(self):
        with Server(lambda r: {"id": r["id"], "ok": False, "error": "not ready"} if r["cmd"] == "screenshot" else ok(r)) as server:
            with DevClient(server.port) as client:
                with self.assertRaisesRegex(DevError, "not ready"):
                    client.call("screenshot")
                self.assertEqual(client.call("ping")["id"], 2)

    def test_wire_protocol_refusals_close_connection(self):
        replies = [b"not JSON\n", b"[]\n", b'{"id":1,"id":1,"ok":true}\n',
                   b'{"id":1,"ok":true,"value":NaN}\n', b'{"id":true,"ok":true}\n',
                   b'{"id":1,"ok":true,"value":1e9999}\n',
                   b'{"id":2,"ok":true}\n', b'{"id":1,"ok":1}\n', b'\xff\n', None]
        for reply in replies:
            with self.subTest(reply=reply):
                with Server(lambda _, data=reply: data) as server:
                    with DevClient(server.port) as client:
                        with self.assertRaises(ProtocolError):
                            client.call("ping")
                        with self.assertRaisesRegex(DevError, "closed"):
                            client.call("ping")

    def test_response_budget_applies_before_json_or_complete_line(self):
        for response in (b"x" * 65, b"x" * 64 + b"\n"):
            with Server(lambda _, data=response: data) as server:
                with DevClient(server.port) as client, patch("scripts.dev_client.MAX_RESPONSE", 64):
                    with self.assertRaisesRegex(ProtocolError, "limit"):
                        client.call("ping")

    def test_request_budget_reserved_fields_and_nonfinite_numbers(self):
        with Server(lambda r: ok(r)) as server:
            with DevClient(server.port) as client:
                for command, args in (("", {}), ("é", {}), ("x"*65, {}), ("ping", {"id": 3}),
                                      ("ping", {"payload": "x"*8192}), ("ping", {"value": float("nan")})):
                    with self.subTest(command=command, args=list(args)):
                        with self.assertRaises((ValueError, TypeError)):
                            client.call(command, **args)
                self.assertEqual(client.call("ping")["id"], 1)
                self.assertEqual(len(server.requests), 1)

    def test_loopback_port_and_timeout_boundaries(self):
        for kwargs in ({"port": 0}, {"port": 65536}, {"port": True}, {"port": 1, "host": "8.8.8.8"},
                       {"port": 1, "timeout": 0}, {"port": 1, "timeout": float("nan")}, {"port": 1, "timeout": 601}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                DevClient(**kwargs)

    def test_capture_metadata_rgb_and_source_preserved(self):
        with Server(capture) as server:
            with DevClient(server.port) as client:
                for source in ("guest", "present"):
                    metadata, rgb = client.capture(source)
                    self.assertEqual(metadata, {"width": 2, "height": 1, "frame": 7, "ticks": 2500000, "frame_ticks": 2400000, "source": source})
                    self.assertEqual(rgb, bytes((1, 2, 3, 253, 254, 255)))
                with self.assertRaises(ValueError):
                    client.capture("desktop")

    def test_capture_geometry_encoding_and_base64_refusals(self):
        invalid = [{"source": "present"}, {"source": "desktop"}, {"encoding": "png"},
                   {"width": 0}, {"width": True}, {"width": 1025}, {"height": 513},
                   {"width": 4_000_001}, {"width": 2000, "height": 2001},
                   {"frame": -1}, {"ticks": 1 << 64}, {"frame": True},
                   {"frame_ticks": None}, {"frame_ticks": True}, {"frame_ticks": -1}, {"frame_ticks": 2500001},
                   {"data": "!!!!!!!!"}, {"data": "AQID"}, {"data": "AA==AA=="}, {"data": 7}]
        for changes in invalid:
            with self.subTest(changes=changes):
                with Server(lambda r, changes=changes: capture(r, **changes)) as server:
                    with DevClient(server.port) as client:
                        with self.assertRaises(ProtocolError):
                            client.capture()

    def test_present_capture_accepts_window_extent_larger_than_guest_limits(self):
        rgb = bytes((17, 29, 43)) * 513
        with Server(lambda r: capture(r, width=1, height=513, data=base64.b64encode(rgb).decode())) as server:
            with DevClient(server.port) as client:
                metadata, received = client.capture("present")
                self.assertEqual(metadata["height"], 513)
                self.assertEqual(received, rgb)

    def test_frame_advance_uses_acknowledged_target_and_waits_paused(self):
        calls = 0
        def respond(request):
            nonlocal calls
            if request["cmd"] == "step_frames":
                self.assertEqual(request["frames"], 3)
                return ok(request, target_frame=15)
            calls += 1
            return ok(request, frame=14 if calls == 1 else 15, paused=calls >= 3)
        with Server(respond) as server:
            with DevClient(server.port) as client:
                result = client.advance(3)
                self.assertEqual(result["frame"], 15)
                self.assertTrue(result["paused"])
                for count in (0, 601, True):
                    with self.assertRaises(ValueError):
                        client.advance(count)
        self.assertEqual(calls, 3)

    def test_reference_advance_is_bounded_and_waits_for_selected_paused_status(self):
        polls = 0
        def respond(request):
            nonlocal polls
            if request['cmd'] == 'reference_frames':
                self.assertEqual(request['frames'], 3)
                return ok(request, target_frame=15)
            self.assertEqual(request['cmd'], 'status')
            polls += 1
            return ok(request, frame=14 if polls == 1 else 15, paused=polls >= 3,
                      host={'execution_policy': execution_policy()})
        with Server(respond) as server, DevClient(server.port) as client:
            result = client.advance(3, reference=True)
            self.assertEqual((result['frame'], result['paused']), (15, True))
            self.assertEqual(result['host']['execution_policy'], execution_policy())
        self.assertEqual([r['cmd'] for r in server.requests], ['reference_frames']+['status']*3)

    def test_reference_advance_refuses_untyped_flags_and_unbounded_counts_before_send(self):
        with Server(lambda r: ok(r)) as server, DevClient(server.port) as client:
            for flag in (0, 1, None, 'true', [], {}):
                with self.subTest(flag=flag), self.assertRaises(ValueError):
                    client.advance(1, reference=flag)
            for count in (0, 601, True, 1.0):
                with self.subTest(count=count), self.assertRaises(ValueError):
                    client.advance(count, reference=True)
        self.assertEqual(server.requests, [])

    def test_reference_advance_rejects_missing_or_unselected_provenance(self):
        for host in (None, {}, {'execution_policy': execution_policy(selected=False)},
                     {'execution_policy': execution_policy() | {'selected': 1}}):
            def respond(request):
                return ok(request, target_frame=1) if request['cmd'] == 'reference_frames' else ok(
                    request, frame=1, paused=True, host=host)
            with self.subTest(host=host), Server(respond) as server, DevClient(server.port) as client:
                with self.assertRaises(ProtocolError):
                    client.advance(1, reference=True)
                with self.assertRaisesRegex(DevError, 'closed'):
                    client.call('ping')

    def test_reference_advance_keeps_one_total_deadline(self):
        def respond(request):
            return ok(request, target_frame=2) if request['cmd'] == 'reference_frames' else ok(
                request, frame=1, paused=False, host={'execution_policy': execution_policy()})
        with Server(respond) as server, DevClient(server.port, timeout=0.04) as client:
            with self.assertRaisesRegex(DevError, 'timed out'):
                client.advance(2, reference=True)
        self.assertEqual(server.requests[0]['cmd'], 'reference_frames')
        self.assertTrue(all(r['cmd'] == 'status' for r in server.requests[1:]))

    def test_fragmentation_does_not_reset_total_response_timeout(self):
        class SlowFragments(list):
            def __iter__(self):
                for piece in super().__iter__():
                    time.sleep(0.01)
                    yield piece
        def respond(request):
            data = json.dumps(ok(request)).encode()+b"\n"
            return SlowFragments([data[n:n+1] for n in range(len(data))])
        with Server(respond) as server:
            with DevClient(server.port, timeout=0.035) as client:
                with self.assertRaises(ProtocolError):
                    client.call("ping")

    def test_frame_advance_refuses_invalid_target_or_paused_metadata(self):
        for target, paused in ((True, True), (-1, True), (1, "yes")):
            with self.subTest(target=target, paused=paused):
                def respond(request):
                    return ok(request, target_frame=target) if request["cmd"] == "step_frames" else ok(request, frame=1, paused=paused)
                with Server(respond) as server:
                    with DevClient(server.port) as client:
                        with self.assertRaises(ProtocolError):
                            client.advance(1)

    def test_png_pixels_chunks_crc_and_exclusive_output(self):
        rgb = bytes((0, 1, 2, 253, 254, 255, 3, 4, 5, 250, 251, 252))
        data = encode_png(2, 2, rgb)
        self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
        offset = 8
        kinds = []
        while offset < len(data):
            length = int.from_bytes(data[offset:offset+4], "big")
            kind = data[offset+4:offset+8]
            payload = data[offset+8:offset+8+length]
            self.assertEqual(int.from_bytes(data[offset+8+length:offset+12+length], "big"), zlib.crc32(kind+payload) & 0xFFFFFFFF)
            kinds.append(kind)
            if kind == b"IHDR":
                self.assertEqual(struct.unpack(">IIBBBBB", payload), (2, 2, 8, 2, 0, 0, 0))
            if kind == b"IDAT":
                self.assertEqual(zlib.decompress(payload), b"\0"+rgb[:6]+b"\0"+rgb[6:])
            offset += length+12
        self.assertEqual(kinds, [b"IHDR", b"IDAT", b"IEND"])
        with tempfile.TemporaryDirectory(prefix="pce-authored-client-") as temporary:
            for extension in (".png", ".ppm"):
                path = Path(temporary)/("authored"+extension)
                write_capture(path, {"width": 2, "height": 2}, rgb)
                original = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    write_capture(path, {"width": 2, "height": 2}, bytes(len(rgb)))
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(original, data if extension == ".png" else b"P6\n2 2\n255\n"+rgb)
            with self.assertRaises(ValueError):
                write_capture(Path(temporary)/"bad.jpg", {"width": 2, "height": 2}, rgb)
            self.assertFalse((Path(temporary)/"bad.jpg").exists())

    def test_cli_screenshot_writes_only_requested_new_file(self):
        with tempfile.TemporaryDirectory(prefix="pce-authored-client-cli-") as temporary:
            output = Path(temporary)/"authored.png"
            with Server(capture) as server, patch("sys.stdout", new_callable=io.StringIO) as stdout:
                self.assertEqual(main(["--port", str(server.port), "screenshot", str(output)]), 0)
                self.assertEqual(json.loads(stdout.getvalue())["source"], "guest")
            self.assertEqual(list(Path(temporary).iterdir()), [output])
            self.assertEqual(output.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_cli_frame_input_keeps_session_until_clear(self):
        def respond(request):
            if request["cmd"] == "step_frames":
                return ok(request, target_frame=3)
            return ok(request, frame=3, paused=True)
        with Server(respond) as server, patch("sys.stdout", new_callable=io.StringIO):
            self.assertEqual(main(["--port", str(server.port), "input", "0x48", "--slot", "2", "--frames", "3", "--resume"]), 0)
        self.assertEqual([r["cmd"] for r in server.requests], ["pause", "set_input", "step_frames", "status", "clear_input", "resume"])
        self.assertEqual(server.requests[1]["mask"], 0x48)
        self.assertEqual(server.requests[1]["port"], 2)

    def test_cli_reference_frames_never_resumes(self):
        def respond(request):
            if request['cmd'] == 'reference_frames':
                self.assertEqual(request['frames'], 3)
                return ok(request, target_frame=3)
            return ok(request, frame=3, paused=True, host={'execution_policy': execution_policy()})
        with Server(respond) as server, patch('sys.stdout', new_callable=io.StringIO) as output:
            self.assertEqual(main(['--port', str(server.port), 'reference-frames', '3']), 0)
            self.assertTrue(json.loads(output.getvalue())['host']['execution_policy']['selected'])
        self.assertEqual([r['cmd'] for r in server.requests], ['pause', 'reference_frames', 'status'])
        with patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
            main(['--port', '1', 'reference-frames', '3', '--resume'])


if __name__ == "__main__":
    unittest.main()
