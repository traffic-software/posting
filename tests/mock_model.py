"""Deterministic OpenAI-compatible mock for a Docker-only browser smoke test."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/demo":
            self.send_error(404)
            return
        body = b"<html><head><title>Smoke Test</title></head><body><h1>Docker browser works</h1></body></html>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        size = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(size))
        messages = request.get("messages", [])
        tool_messages = [item for item in messages if item.get("role") == "tool"]
        if not tool_messages:
            message = self.tool_call("navigate_to_page", {"url": "http://posting-smoke-model:8765/demo"}, "nav")
            finish_reason = "tool_calls"
        elif len(tool_messages) == 1:
            message = self.tool_call("extract_text", {"selector": "h1"}, "extract")
            finish_reason = "tool_calls"
        else:
            message = {"role": "assistant", "content": "Heading: " + str(tool_messages[-1].get("content", ""))[:200]}
            finish_reason = "stop"
        data = json.dumps({
            "id": "chatcmpl-local-smoke", "object": "chat.completion", "created": 1,
            "model": request.get("model", "mock"),
            "choices": [{"index": 0, "message": message, "finish_reason": finish_reason}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
        }).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    @staticmethod
    def tool_call(name, arguments, suffix):
        return {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_" + suffix, "type": "function", "function": {
                "name": name, "arguments": json.dumps(arguments)
            }}
        ]}


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
