"""Authored mathematical CAS witnesses, independent of the host implementation."""
import copy
import unittest

from scripts.dev_observation import MAX_COUNTER, ObservationError, validate_paused_observation
from scripts.dev_write import (
    LINEAR_RAM, POPULOUS_RAM, WORK_RAM_MIRRORS, validate_paused_write,
)


def witness():
    """Three changed data bytes in a bank which also contains current code."""
    memory = bytearray(8192)
    code = [0x80, 0xFE, 0xEA, 0xEA, 0xEA, 0xEA, 0xEA]
    memory[0x200:0x207] = bytes(code)
    before = {
        "id": 10, "ok": True, "paused": True, "local_paused": False,
        "frame": 123, "ticks": 456,
        "host": {
            "pc": 0x2200, "native_steps": 700, "interpreter_steps": 9,
            "debug_memory": {"write_enabled": True, "write_requests": 9, "bytes_changed": 13},
            "cpu": {"a": 2, "x": 3, "p": 4,
                    "mpr": [255, 249, 128, 129, 130, 131, 132, 0],
                    "physical_pc": 0x1F2200,
                    "instruction_physical": list(range(0x1F2200, 0x1F2207)),
                    "instruction_bytes": code,
                    "instruction_generations": [17] * 7},
            "audio_output": {"frames": 19, "pending": 3},
        },
        "future": {"counter": 1, "items": [False, None, "a"]},
    }
    after = copy.deepcopy(before)
    after["id"] = 99
    after["host"]["debug_memory"].update(write_requests=10, bytes_changed=16)
    after["host"]["cpu"]["instruction_generations"] = [20] * 7
    output = bytearray(memory)
    output[0x500:0x504] = b"\x01\x00\x02\x03"
    return {
        "before": before, "after": after,
        "request": {"id": 12, "cmd": "write_memory", "address": 0x1F2500,
                    "data": "01000203", "expected": "00000000"},
        "acknowledgement": {"id": 12, "ok": True, "address": 0x1F2500, "length": 4},
        "memory_before": bytes(memory), "memory_after": bytes(output),
        "profile": WORK_RAM_MIRRORS,
        "code_footprint": frozenset(range(0x1F0200, 0x1F0207)),
    }


def validate(row):
    return validate_paused_write(**row)


class PausedWriteTests(unittest.TestCase):
    def test_wram_data_changes_same_executing_bank_exactly(self):
        row = witness()
        original = copy.deepcopy(row)
        result = validate(row)
        self.assertEqual(result["bytes_changed_delta"], 3)
        self.assertEqual(result["bank_generation_deltas"], [
            {"bank": 248, "delta": 3}, {"bank": 249, "delta": 3},
            {"bank": 250, "delta": 3}, {"bank": 251, "delta": 3}])
        self.assertEqual(result["fetched_generation_deltas"], [3] * 7)
        self.assertEqual(result["memory_bytes"], 8192)
        self.assertEqual(row, original)
        # The ordinary comparison remains strict; effect validation is separate.
        with self.assertRaises(ObservationError):
            validate_paused_observation(row["before"], row["after"])

    def test_noop_still_counts_request_without_generation_or_changed_bytes(self):
        row = witness()
        row["request"]["data"] = row["request"]["expected"]
        row["memory_after"] = row["memory_before"]
        row["after"]["host"]["debug_memory"]["bytes_changed"] = 13
        row["after"]["host"]["cpu"]["instruction_generations"] = [17] * 7
        proof = validate(row)
        self.assertEqual(proof["bank_generation_deltas"], [])
        self.assertEqual(proof["write_requests_delta"], 1)

    def test_all_four_request_aliases_and_uppercase_hex(self):
        for bank in range(248, 252):
            row = witness()
            row["request"]["address"] = row["acknowledgement"]["address"] = (bank << 13) + 0x500
            row["request"]["data"] = "0A000B0C"
            out = bytearray(row["memory_before"])
            out[0x500:0x504] = b"\x0A\0\x0B\x0C"
            row["memory_after"] = bytes(out)
            with self.subTest(bank=bank):
                self.assertEqual(validate(row)["bytes_changed_delta"], 3)

    def test_alias_bank_boundary_wraps_backing_not_readback_index(self):
        row = witness()
        row["request"].update(address=0x1F3FFF, data="010002", expected="000000")
        row["acknowledgement"].update(address=0x1F3FFF, length=3)
        out = bytearray(row["memory_before"])
        out[8191], out[0], out[1] = 1, 0, 2
        row["memory_after"] = bytes(out)
        row["after"]["host"]["debug_memory"]["bytes_changed"] = 15
        row["after"]["host"]["cpu"]["instruction_generations"] = [19] * 7
        self.assertEqual(validate(row)["bytes_changed_delta"], 2)

    def test_fetch_page_crossing_and_logical_wrap(self):
        for pc, mpr, physical in (
                (0x1FFD, [248, 249, 128, 129, 130, 131, 132, 0],
                 [0x1F1FFD, 0x1F1FFE, 0x1F1FFF, 0x1F2000, 0x1F2001, 0x1F2002, 0x1F2003]),
                (0xFFFD, [249, 248, 128, 129, 130, 131, 132, 248],
                 [0x1F1FFD, 0x1F1FFE, 0x1F1FFF, 0x1F2000, 0x1F2001, 0x1F2002, 0x1F2003])):
            row = witness()
            memory = bytearray(row["memory_before"])
            for i, addr in enumerate(physical):
                memory[addr & 8191] = row["before"]["host"]["cpu"]["instruction_bytes"][i]
            row["memory_before"] = bytes(memory)
            memory[0x500:0x504] = b"\x01\0\x02\x03"
            row["memory_after"] = bytes(memory)
            for name in ("before", "after"):
                row[name]["host"]["pc"] = pc
                row[name]["host"]["cpu"].update(
                    mpr=mpr, physical_pc=physical[0], instruction_physical=physical)
            with self.subTest(pc=pc):
                self.assertEqual(validate(row)["fetched_generation_deltas"], [3] * 7)

    def test_linear_two_bank_write_has_per_bank_delta(self):
        row = witness()
        memory = bytearray(16384)
        memory[:7] = bytes(row["before"]["host"]["cpu"]["instruction_bytes"])
        row.update(profile=LINEAR_RAM, memory_base=0x6000,
                   memory_before=bytes(memory), code_footprint={0x6000, 0x6001})
        memory[8191:8193] = b"\x01\x02"
        row["memory_after"] = bytes(memory)
        row["request"].update(address=0x7FFF, data="0102", expected="0000")
        row["acknowledgement"].update(address=0x7FFF, length=2)
        row["after"]["host"]["debug_memory"]["bytes_changed"] = 15
        for name, generation in (("before", 17), ("after", 18)):
            row[name]["host"]["pc"] = 0xE000
            row[name]["host"]["cpu"].update(
                mpr=[255, 248, 128, 129, 130, 131, 132, 3], physical_pc=0x6000,
                instruction_physical=list(range(0x6000, 0x6007)),
                instruction_generations=[generation] * 7)
        proof = validate(row)
        self.assertEqual(proof["bank_generation_deltas"], [{"bank": 3, "delta": 1}, {"bank": 4, "delta": 1}])

    def test_fetch_crosses_affected_wram_and_unaffected_rom(self):
        row = witness()
        physical = [0x1F1FFD, 0x1F1FFE, 0x1F1FFF, 0, 1, 2, 3]
        memory = bytearray(row["memory_before"])
        memory[0x1FFD:] = bytes(row["before"]["host"]["cpu"]["instruction_bytes"][:3])
        row["memory_before"] = bytes(memory)
        memory[0x500:0x504] = b"\x01\0\x02\x03"
        row["memory_after"] = bytes(memory)
        for name in ("before", "after"):
            row[name]["host"]["pc"] = 0x1FFD
            row[name]["host"]["cpu"].update(
                mpr=[248, 0, 128, 129, 130, 131, 132, 0],
                physical_pc=physical[0], instruction_physical=physical)
        row["before"]["host"]["cpu"]["instruction_generations"] = [17] * 3 + [7] * 4
        row["after"]["host"]["cpu"]["instruction_generations"] = [20] * 3 + [7] * 4
        self.assertEqual(validate(row)["fetched_generation_deltas"], [3, 3, 3, 0, 0, 0, 0])
        row["after"]["host"]["cpu"]["instruction_generations"] = [20] * 3 + [10] * 4
        with self.assertRaises(ObservationError):
            validate(row)

    def test_populous_eight_alias_groups_and_code_alias_exclusion(self):
        for bank in range(0x40, 0x60):
            row = witness()
            row.update(profile=POPULOUS_RAM, code_footprint=set())
            data = bytearray(32768)
            row["memory_before"] = bytes(data)
            offset = ((bank & 3) << 13) + 0x500
            data[offset:offset + 4] = b"\x01\0\x02\x03"
            row["memory_after"] = bytes(data)
            address = (bank << 13) + 0x500
            row["request"]["address"] = row["acknowledgement"]["address"] = address
            # Current WRAM execution is outside the cartridge RAM being edited.
            row["after"]["host"]["cpu"]["instruction_generations"] = [17] * 7
            with self.subTest(bank=bank):
                proof = validate(row)
                self.assertEqual([r["bank"] for r in proof["bank_generation_deltas"]],
                                 list(range(0x40 + (bank & 3), 0x60, 4)))
                row["code_footprint"] = {0x80000 + offset}
                with self.assertRaises(ObservationError):
                    validate(row)

    def test_fetched_byte_or_historical_alias_edit_refused_even_noop(self):
        for address in (0x1F0200, 0x1F2200, 0x1F4200, 0x1F6200):
            row = witness()
            row["request"].update(address=address, data="80", expected="80")
            row["acknowledgement"].update(address=address, length=1)
            with self.subTest(address=address), self.assertRaises(ObservationError):
                validate(row)
        row = witness()
        row["code_footprint"] = {0x1F6500}
        with self.assertRaises(ObservationError):
            validate(row)

    def test_all_unrelated_status_fields_and_types_remain_strict(self):
        paths = [("ticks",), ("frame",), ("host", "pc"),
                 ("host", "native_steps"), ("host", "interpreter_steps"),
                 ("host", "cpu", "a"), ("host", "cpu", "mpr", 0),
                 ("host", "cpu", "instruction_bytes", 0),
                 ("host", "audio_output", "frames"), ("future", "counter")]
        for path in paths:
            for replacement in (True, 1.0, 100000):
                row = witness()
                obj = row["after"]
                for part in path[:-1]:
                    obj = obj[part]
                obj[path[-1]] = replacement
                with self.subTest(path=path, replacement=replacement), self.assertRaises(ObservationError):
                    validate(row)

    def test_complete_memory_literal_and_fetched_readback_required(self):
        for option in ("stale", "outside", "short", "wrong-code", "mutable"):
            row = witness()
            if option == "stale":
                row["request"]["expected"] = "01000000"
            elif option == "outside":
                out = bytearray(row["memory_after"]); out[700] = 99
                row["memory_after"] = bytes(out)
            elif option == "short":
                row["memory_before"] = row["memory_before"][:-1]
                row["memory_after"] = row["memory_after"][:-1]
            elif option == "wrong-code":
                for key in ("memory_before", "memory_after"):
                    out = bytearray(row[key]); out[0x200] = 0
                    row[key] = bytes(out)
            else:
                row["memory_before"] = bytearray(row["memory_before"])
            with self.subTest(option=option), self.assertRaises(ObservationError):
                validate(row)

    def test_exact_request_ack_and_connection_order(self):
        for field, value in (("id", True), ("id", 10), ("id", 99), ("cmd", "read_memory"),
                             ("address", True), ("data", "0x01"), ("data", "00 00"),
                             ("data", "0"), ("data", "GG"), ("expected", "00")):
            row = witness(); row["request"][field] = value
            with self.subTest(request=field, value=value), self.assertRaises(ObservationError):
                validate(row)
        for field, value in (("id", 13), ("id", True), ("ok", 1), ("ok", False),
                             ("address", 0), ("length", True), ("length", 3)):
            row = witness(); row["acknowledgement"][field] = value
            with self.subTest(ack=field, value=value), self.assertRaises(ObservationError):
                validate(row)
        for key in ("request", "acknowledgement"):
            row = witness(); row[key]["extra"] = 0
            with self.subTest(key=key), self.assertRaises(ObservationError):
                validate(row)

    def test_counter_generation_and_overflow_refusals(self):
        for key in ("write_requests", "bytes_changed"):
            for value in (True, -1, MAX_COUNTER + 1, 999):
                row = witness(); row["after"]["host"]["debug_memory"][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ObservationError):
                    validate(row)
            row = witness(); row["before"]["host"]["debug_memory"][key] = MAX_COUNTER
            with self.assertRaises(ObservationError):
                validate(row)
        for value in (True, -1, MAX_COUNTER + 1, 17, 19, 21):
            row = witness(); row["after"]["host"]["cpu"]["instruction_generations"] = [value] * 7
            with self.subTest(generation=value), self.assertRaises(ObservationError):
                validate(row)
        row = witness(); row["before"]["host"]["cpu"]["instruction_generations"] = [MAX_COUNTER - 2] * 7
        with self.assertRaises(ObservationError):
            validate(row)

    def test_profile_footprint_optin_and_source_shape_refusals(self):
        for profile in (None, True, "abi26", "auto"):
            row = witness(); row["profile"] = profile
            with self.subTest(profile=profile), self.assertRaises(ObservationError):
                validate(row)
        for footprint in (None, {}, iter(()), [True], [-1], [0x200000]):
            row = witness(); row["code_footprint"] = footprint
            with self.subTest(footprint=repr(footprint)), self.assertRaises(ObservationError):
                validate(row)
        for path, value in ((["host", "debug_memory", "write_enabled"], False),
                            (["paused"], False), (["local_paused"], True),
                            (["host", "cpu", "instruction_bytes"], [None] * 7),
                            (["host", "cpu", "instruction_physical"], []),
                            (["host", "cpu", "mpr"], [248] * 7)):
            row = witness(); obj = row["before"]
            for key in path[:-1]: obj = obj[key]
            obj[path[-1]] = value
            with self.subTest(path=path), self.assertRaises(ObservationError):
                validate(row)

    def test_unknown_fields_stay_exact_and_nonfinite_never_admitted(self):
        for where in ("host", "cpu", "debug_memory"):
            row = witness()
            obj = row["after"]["host"]
            if where != "host": obj = obj[where]
            obj["new_field"] = 0
            with self.subTest(where=where), self.assertRaises(ObservationError):
                validate(row)
        for value in (float("nan"), float("inf"), float("-inf")):
            row = witness()
            for name in ("before", "after"):
                row[name]["future"]["same_unknown_float"] = value
            with self.subTest(value=value), self.assertRaises(ObservationError):
                validate(row)

    def test_declared_topology_bounds_and_fetched_bank_consistency(self):
        for changes in ({"memory_base": True}, {"memory_base": 0},
                        {"profile": LINEAR_RAM},
                        {"profile": LINEAR_RAM, "memory_base": 0x1F0001},
                        {"profile": POPULOUS_RAM},):
            row = witness(); row.update(changes)
            with self.subTest(changes=changes), self.assertRaises(ObservationError):
                validate(row)
        for field, value in (("physical_pc", 0),
                             ("instruction_generations", [17, 18, 17, 17, 17, 17, 17])):
            row = witness(); row["before"]["host"]["cpu"][field] = value
            with self.subTest(field=field), self.assertRaises(ObservationError):
                validate(row)
        row = witness()
        row["request"].update(address=0x1F7FFF, data="0102", expected="0000")
        row["acknowledgement"].update(address=0x1F7FFF, length=2)
        with self.assertRaises(ObservationError):
            validate(row)


if __name__ == "__main__":
    unittest.main()
