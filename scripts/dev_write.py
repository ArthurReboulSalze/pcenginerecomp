"""Pure, explicit effects of one successful paused physical-RAM CAS.

This validates retained evidence; it never authorizes, sends or retries a write.
The caller must independently bind the host/source and declared RAM topology,
retain raw wire replies before validation, and supply a complete original/live
code footprint. A supplied footprint is not authenticated by this helper. Game
register copies and other title-level edit invariants remain the caller's job.
"""
from __future__ import annotations

import copy
import hashlib

from scripts.dev_observation import (
    MAX_COUNTER, MAX_REQUEST_ID, ObservationError, validate_paused_observation,
)

WORK_RAM_MIRRORS = "work-ram-mirrors-v1"
LINEAR_RAM = "linear-ram-v1"
POPULOUS_RAM = "populous-ram-v1"
_PHYSICAL_SIZE = 0x200000
_BANK_SIZE = 8192


def _require(value, message):
    if not value:
        raise ObservationError(message)


def _integer(value, minimum, maximum, label):
    _require(type(value) is int and minimum <= value <= maximum,
             label + ": exact bounded integer required")
    return value


def _hex(value, label):
    _require(type(value) is str and 2 <= len(value) <= 512 and len(value) % 2 == 0
             and all(char in "0123456789abcdefABCDEF" for char in value),
             label + ": 1..256 contiguous hex bytes required")
    return bytes.fromhex(value)


def _region(profile, memory_base, size):
    _require(type(profile) is str and profile in (
        WORK_RAM_MIRRORS, LINEAR_RAM, POPULOUS_RAM), "explicit RAM topology required")
    if profile == WORK_RAM_MIRRORS:
        _require(memory_base is None or type(memory_base) is int and memory_base == 0x1F0000,
                 "WRAM canonical base must be 0x1F0000")
        _require(size == 8192, "complete 8192-byte WRAM backing required")
        return 0x1F0000, 0x1F0000, 0x1F8000
    if profile == POPULOUS_RAM:
        _require(memory_base is None or type(memory_base) is int and memory_base == 0x80000,
                 "Populous canonical base must be 0x80000")
        _require(size == 32768, "complete 32768-byte cartridge RAM backing required")
        return 0x80000, 0x80000, 0xC0000
    _integer(memory_base, 0, _PHYSICAL_SIZE - _BANK_SIZE, "linear RAM base")
    _require(memory_base % _BANK_SIZE == 0 and size % _BANK_SIZE == 0
             and _BANK_SIZE <= size <= _PHYSICAL_SIZE - memory_base,
             "complete aligned linear RAM bank region required")
    return memory_base, memory_base, memory_base + size


def _backing(address, profile):
    if profile == WORK_RAM_MIRRORS and 0x1F0000 <= address < 0x1F8000:
        return 0x1F0000 | (address & 8191)
    if profile == POPULOUS_RAM and 0x80000 <= address < 0xC0000:
        return 0x80000 | (address & 32767)
    return address


def _affected_banks(address, profile):
    if profile == WORK_RAM_MIRRORS:
        return range(0xF8, 0xFC)
    if profile == POPULOUS_RAM:
        return range(0x40 + ((address >> 13) & 3), 0x60, 4)
    return (address >> 13,)


def _cpu(status):
    host = status["host"]
    _integer(host.get("pc"), 0, 65535, "logical PC")
    cpu = host.get("cpu")
    _require(type(cpu) is dict, "complete CPU observation required")
    mpr = cpu.get("mpr")
    _require(type(mpr) is list and len(mpr) == 8, "all eight MPRs required")
    for value in mpr:
        _integer(value, 0, 255, "MPR")
    for key, maximum in (("instruction_physical", 0x1FFFFF),
                         ("instruction_bytes", 255),
                         ("instruction_generations", MAX_COUNTER)):
        values = cpu.get(key)
        _require(type(values) is list and len(values) == 7,
                 "complete seven-byte " + key + " required")
        for value in values:
            _integer(value, 0, maximum, key)
    physical = [((mpr[((host["pc"] + i) & 65535) >> 13] << 13)
                 | ((host["pc"] + i) & 8191)) for i in range(7)]
    _integer(cpu.get("physical_pc"), 0, 0x1FFFFF, "physical PC")
    _require(cpu["physical_pc"] == physical[0] and cpu["instruction_physical"] == physical,
             "logical PC/MPR/fetched physical mapping differs")
    seen = {}
    for address, generation in zip(physical, cpu["instruction_generations"]):
        bank = address >> 13
        _require(bank not in seen or seen[bank] == generation,
                 "one fetched bank reports inconsistent generations")
        seen[bank] = generation
    return cpu


def validate_paused_write(before, after, *, request, acknowledgement,
                          memory_before, memory_after, profile, code_footprint,
                          memory_base=None):
    """Validate one explicitly declared CAS and its complete RAM readback.

    ``request`` is the exact parsed wire object (id/cmd/address/data/expected);
    ``acknowledgement`` is its successful id/ok/address/length reply. Their IDs
    must occur strictly between the two status IDs in one connection. Full
    canonical backing readbacks are bytes: 8 KiB for WORK_RAM_MIRRORS, 32 KiB
    for POPULOUS_RAM, or an explicitly declared aligned, whole-bank linear RAM
    region. A profile is a declaration, not proof that the host uses it.

    Every submitted byte, including unchanged bytes, must avoid current fetched
    bytes and all supplied historical/live code addresses through backing aliases.
    A complete supplied footprint still cannot predict future code or certify
    game-level safety. Only debug counters and exactly predicted current-fetch
    bank generation deltas are admitted. Every other reported field, including
    unknown fields, passes the unchanged STRICT observer. No audio-drain profile
    is composed, and omitted/non-current bank generations are not observed.
    Returned bank_generation_deltas predict all affected banks; only the seven
    fetched generation positions are measured by the status pair. The nested
    strict_projection describes the normalized object, not original generation
    equality. Full status schema/build/profile authentication stays with callers.
    """
    # Validate finite plain JSON and pause/type contracts before any projection.
    validate_paused_observation(before, before)
    validate_paused_observation(after, after)
    _require(type(request) is dict and request.keys() == {
        "id", "cmd", "address", "data", "expected"}, "exact CAS request fields required")
    _require(type(request["cmd"]) is str and request["cmd"] == "write_memory",
             "write_memory request required")
    identity = _integer(request["id"], 1, MAX_REQUEST_ID, "CAS request ID")
    address = _integer(request["address"], 0, 0x1FFFFF, "CAS physical address")
    data, expected = _hex(request["data"], "CAS data"), _hex(request["expected"], "CAS expected")
    _require(len(data) == len(expected) and len(data) <= _PHYSICAL_SIZE - address,
             "CAS lengths or physical range differ")
    _require(type(acknowledgement) is dict and acknowledgement.keys() == {
        "id", "ok", "address", "length"}, "exact successful CAS ACK fields required")
    _integer(acknowledgement["id"], 1, MAX_REQUEST_ID, "CAS ACK ID")
    _integer(acknowledgement["address"], 0, 0x1FFFFF, "CAS ACK address")
    _integer(acknowledgement["length"], 1, 256, "CAS ACK length")
    _require(acknowledgement["ok"] is True and acknowledgement["id"] == identity
             and acknowledgement["address"] == address
             and acknowledgement["length"] == len(data), "CAS ACK differs from request")
    _require(before["id"] < identity < after["id"],
             "status/CAS IDs must be ordered within one connection")
    _require(type(memory_before) is bytes and type(memory_after) is bytes
             and len(memory_before) == len(memory_after), "complete exact byte readbacks required")
    base, low, high = _region(profile, memory_base, len(memory_before))
    _require(low <= address and address + len(data) <= high,
             "CAS request outside declared RAM mapping")
    _require(type(code_footprint) in (list, tuple, set, frozenset)
             and len(code_footprint) <= _PHYSICAL_SIZE,
             "bounded original/live code footprint required")
    for value in code_footprint:
        _integer(value, 0, 0x1FFFFF, "code footprint physical byte")
    protected = {_backing(value, profile) for value in code_footprint}
    left_cpu, right_cpu = _cpu(before), _cpu(after)
    protected.update(_backing(value, profile) for value in left_cpu["instruction_physical"])
    offsets = [_backing(address + i, profile) - base for i in range(len(data))]
    _require(all(base + offset not in protected for offset in offsets),
             "submitted RAM byte aliases observed or current code")
    predicted = bytearray(memory_before)
    deltas = {}
    changed = 0
    for index, offset in enumerate(offsets):
        _require(memory_before[offset] == expected[index], "CAS literal expected bytes differ")
        if expected[index] != data[index]:
            changed += 1
            for bank in _affected_banks(address + index, profile):
                deltas[bank] = deltas.get(bank, 0) + 1
        predicted[offset] = data[index]
    _require(memory_after == bytes(predicted), "complete RAM readback differs outside declared CAS")
    for cpu, memory in ((left_cpu, memory_before), (right_cpu, memory_after)):
        for physical, byte in zip(cpu["instruction_physical"], cpu["instruction_bytes"]):
            backing = _backing(physical, profile)
            if base <= backing < base + len(memory):
                _require(memory[backing - base] == byte, "fetched bytes differ from complete RAM backing")
    projected = copy.deepcopy(after)
    debug = before["host"].get("debug_memory")
    post_debug = after["host"].get("debug_memory")
    _require(type(debug) is dict and type(post_debug) is dict
             and debug.get("write_enabled") is True and post_debug.get("write_enabled") is True,
             "explicit host RAM write opt-in required")
    for key, delta in (("write_requests", 1), ("bytes_changed", changed)):
        start = _integer(debug.get(key), 0, MAX_COUNTER, "debug." + key)
        end = _integer(post_debug.get(key), 0, MAX_COUNTER, "debug." + key)
        _require(start <= MAX_COUNTER - delta and end == start + delta,
                 "exact nonoverflowing debug counter delta required: " + key)
        projected["host"]["debug_memory"][key] = start
    generation_deltas = []
    for index, (physical, initial, final) in enumerate(zip(
            left_cpu["instruction_physical"], left_cpu["instruction_generations"],
            right_cpu["instruction_generations"])):
        delta = deltas.get(physical >> 13, 0)
        _require(initial <= MAX_COUNTER - delta and final == initial + delta,
                 "exact nonoverflowing fetched-bank generation delta required")
        projected["host"]["cpu"]["instruction_generations"][index] = initial
        generation_deltas.append(delta)
    strict = validate_paused_observation(before, projected)
    return {
        "schema": 1, "profile": profile,
        "transport_ids": {"before": before["id"], "write": identity, "after": after["id"]},
        "address": address, "length": len(data), "memory_base": base,
        "memory_bytes": len(memory_before), "write_requests_delta": 1,
        "bytes_changed_delta": changed,
        "bank_generation_deltas": [{"bank": bank, "delta": deltas[bank]} for bank in sorted(deltas)],
        "bank_generation_deltas_are_predictions": True,
        "fetched_generation_deltas": generation_deltas,
        "observed_generation_scope": "seven-current-fetch-positions",
        "memory_before_sha256": hashlib.sha256(memory_before).hexdigest(),
        "memory_after_sha256": hashlib.sha256(memory_after).hexdigest(),
        "supplied_code_footprint_count": len(code_footprint),
        "submitted_bytes_exclude_supplied_and_current_code": True,
        "strict_projection_scope": "after normalizing declared debug and fetched-generation effects",
        "strict_projection": strict,
    }
