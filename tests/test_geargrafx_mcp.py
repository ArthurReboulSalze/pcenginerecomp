"""Authored original-reference transport admission, independent of emulator state."""
import json
import unittest
from unittest.mock import patch

from scripts.reference_geargrafx import Mcp, MCP_HTTP_TIMEOUT_SECONDS, MCP_MAX_RESPONSE_BYTES


def encoded(value):
    return json.dumps(value).encode("utf-8")


def envelope(result=None, **changes):
    value = dict(jsonrpc="2.0", id=1, result={} if result is None else result)
    value.update(changes)
    return value


class Response:
    def __init__(self, body, *, status=200, headers=None):
        self.body = body
        self.status = status
        self.headers = {"Content-Type": "application/json", **(headers or {})}
        self.read_sizes = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        self.read_sizes.append(size)
        return self.body[:size]


class GearMcpTests(unittest.TestCase):
    def rpc(self, body, **response_options):
        client = Mcp(12345)
        response = Response(body, **response_options)
        with patch("scripts.reference_geargrafx.urllib.request.urlopen", return_value=response) as opened:
            result = client.rpc("tools/list")
        return result, client, response, opened

    def tool(self, result):
        with patch("scripts.reference_geargrafx.urllib.request.urlopen", return_value=Response(encoded(envelope(result)))):
            return Mcp(12345).call("authored_tool", count=2)

    def test_matching_response_extensions_and_transport_bounds(self):
        result, client, response, opened = self.rpc(encoded(envelope(
            {"tools": [], "optional": {"latency": .125}}, extension="allowed")),
            headers={"Mcp-Session-Id": "test-session", "Content-Type": "Application/JSON; charset=utf-8"})
        self.assertEqual(result, {"tools": [], "optional": {"latency": .125}})
        self.assertEqual(client.headers["Mcp-Session-Id"], "test-session")
        self.assertEqual(response.read_sizes, [MCP_MAX_RESPONSE_BYTES + 1])
        self.assertEqual(opened.call_args.kwargs, {"timeout": MCP_HTTP_TIMEOUT_SECONDS})
        request = json.loads(opened.call_args.args[0].data)
        self.assertEqual(request, dict(jsonrpc="2.0", id=1, method="tools/list", params={}))

    def test_successive_ids_and_optional_session(self):
        client = Mcp(12345)
        with patch("scripts.reference_geargrafx.urllib.request.urlopen", side_effect=[
                Response(encoded(envelope())), Response(encoded(envelope(id=2)))]) as opened:
            self.assertEqual(client.rpc("initialize"), {})
            self.assertEqual(client.rpc("tools/list"), {})
        self.assertNotIn("Mcp-Session-Id", client.headers)
        self.assertEqual([json.loads(call.args[0].data)["id"] for call in opened.call_args_list], [1, 2])

    def test_actual_gear_notification_contract(self):
        client = Mcp(12345)
        with patch("scripts.reference_geargrafx.urllib.request.urlopen", return_value=Response(b"", status=202)) as opened:
            self.assertEqual(client.rpc("notifications/initialized"), {})
        self.assertNotIn("id", json.loads(opened.call_args.args[0].data))
        for status, body in [(200, b""), (202, b"{}"), (202, encoded(envelope())), (204, b"")]:
            with self.subTest(status=status, body=body):
                with patch("scripts.reference_geargrafx.urllib.request.urlopen", return_value=Response(body, status=status)):
                    with self.assertRaisesRegex(RuntimeError, "notification"):
                        Mcp(12345).rpc("notifications/initialized")

    def test_wrong_and_missing_ids_rejected_even_numeric_lookalikes(self):
        values = [envelope(id=value) for value in [True, False, 1.0, "1", None, 0, 2]]
        missing = envelope()
        del missing["id"]
        for value in [*values, missing]:
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, "id"):
                self.rpc(encoded(value))

    def test_invalid_response_envelopes(self):
        missing_version = envelope()
        del missing_version["jsonrpc"]
        cases = [[], None, 4, "response", envelope(jsonrpc="1.0"), missing_version,
            dict(jsonrpc="2.0", id=1), envelope(error={"code": -1, "message": "no"}),
            envelope(result=[]), envelope(result=False)]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                self.rpc(encoded(value))

    def test_protocol_errors_are_typed_and_explicit(self):
        for error in [None, [], {}, {"code": True, "message": "bad"},
                {"code": 1.0, "message": "bad"}, {"code": -1, "message": 5}]:
            with self.subTest(error=error), self.assertRaisesRegex(RuntimeError, "error envelope"):
                self.rpc(encoded(dict(jsonrpc="2.0", id=1, error=error)))
        with self.assertRaisesRegex(RuntimeError, "MCP protocol error: -32601: unknown tool"):
            self.rpc(encoded(dict(jsonrpc="2.0", id=1,
                error=dict(code=-32601, message="unknown tool", data={"optional": 2}))))

    def test_outer_duplicate_keys_and_nonfinite_numbers(self):
        bodies = [b'{"jsonrpc":"2.0","id":9,"id":1,"result":{}}',
            b'{"jsonrpc":"2.0","id":1,"result":{},"result":{}}',
            b'{"jsonrpc":"2.0","id":1,"result":{"x":{"a":1,"a":2}}}']
        bodies += [b'{"jsonrpc":"2.0","id":1,"result":{"x":'+token+b'}}'
                   for token in [b"NaN", b"Infinity", b"-Infinity", b"1e9999", b"-1e9999"]]
        for body in bodies:
            with self.subTest(body=body), self.assertRaisesRegex(RuntimeError, "JSON"):
                self.rpc(body)

    def test_empty_invalid_encoding_and_syntax(self):
        for body in [b"", b"\xff", b"{} trailing", b"\xff\xfe{\x00}\x00"]:
            with self.subTest(body=body[:20]), self.assertRaisesRegex(RuntimeError, "JSON"):
                self.rpc(body)

    def test_exact_body_bound_and_overflow(self):
        base = encoded(envelope())
        self.assertEqual(self.rpc(base + b" " * (MCP_MAX_RESPONSE_BYTES-len(base)))[0], {})
        with self.assertRaisesRegex(RuntimeError, "exceeded 2 MiB"):
            self.rpc(base + b" " * (MCP_MAX_RESPONSE_BYTES+1-len(base)))

    def test_http_profile_errors_and_timeout_propagation(self):
        for status, content_type in [(202, "application/json"), (200, "text/event-stream"),
                (200, "text/html"), (204, "application/json")]:
            with self.subTest(status=status, content_type=content_type), self.assertRaisesRegex(RuntimeError, "HTTP 200"):
                self.rpc(encoded(envelope()), status=status, headers={"Content-Type": content_type})
        # Startup callers intentionally catch OSError to retry a not-yet-listening isolated server.
        with patch("scripts.reference_geargrafx.urllib.request.urlopen", side_effect=TimeoutError("test timeout")):
            with self.assertRaisesRegex(TimeoutError, "test timeout"):
                Mcp(12345).rpc("initialize")

    def test_rejected_response_cannot_poison_session(self):
        client = Mcp(12345)
        client.headers["Mcp-Session-Id"] = "original"
        for body, session in [(encoded(envelope(id=5)), "replacement"),
                (encoded(envelope()), "has space"), (encoded(envelope()), ""),
                (encoded(envelope()), "bad\r\nheader"), (encoded(envelope()), "nonascii\u00e9")]:
            with self.subTest(session=session):
                with patch("scripts.reference_geargrafx.urllib.request.urlopen", return_value=Response(body,
                        headers={"Mcp-Session-Id": session})):
                    with self.assertRaises(RuntimeError):
                        client.rpc("tools/list")
                self.assertEqual(client.headers["Mcp-Session-Id"], "original")
                client.sequence = 0

    def test_existing_tool_payload_shape_and_optional_content_preserved(self):
        payload = {"PC": "E000", "MPR": [{"index": 0, "value": "FF"}], "fraction": .5}
        self.assertEqual(self.tool(dict(content=[dict(type="text", text=json.dumps(payload))],
            isError=False, structuredContent={"optional": True})), payload)
        self.assertEqual(self.tool(dict(content=[dict(type="image", data="authored", mimeType="image/png"),
            dict(type="text", text='[1,2,3]')])), [1, 2, 3])

    def test_nested_tool_json_is_strict(self):
        texts = ['{"key":1,"key":2}', '{"inside":{"key":1,"key":2}}',
            '{"value":NaN}', '{"value":Infinity}', '{"value":1e9999}', 'not JSON']
        for text in texts:
            with self.subTest(text=text[:40]), self.assertRaisesRegex(RuntimeError, "reference tool authored_tool JSON"):
                self.tool(dict(content=[dict(type="text", text=text)]))

    def test_tool_error_and_malformed_content_fail_explicitly(self):
        with self.assertRaisesRegex(RuntimeError, "Reference tool failed"):
            self.tool(dict(isError=True, content=[dict(type="text", text="failure")]))
        for flag in [0, 1, "false", None, []]:
            with self.subTest(flag=flag), self.assertRaisesRegex(RuntimeError, "isError"):
                self.tool(dict(isError=flag, content=[dict(type="text", text="{}")]))
        for content in [None, {}, [], [None], [{}], [dict(type=2)], [dict(type="text")],
                [dict(type="text", text=1)], [dict(type="text", text="{}"), dict(type="text", text="{}")]]:
            with self.subTest(content=content), self.assertRaises(RuntimeError):
                self.tool(dict(content=content))


if __name__ == "__main__":
    unittest.main()
