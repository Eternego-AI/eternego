from application.platform.processes import on_separate_process_async

async def test_feed_succeeds_with_anthropic_data():
    def isolated():
        import tempfile
        import os
        import json
        import asyncio
        import threading
        from application.core import agents, gateways
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.business import persona as spec
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                path = self.path
                if path == "/api/chat":
                    self.wfile.write(json.dumps({"message": {"content": "ok"}}).encode())
                elif path == "/api/generate":
                    self.wfile.write(json.dumps({"response": "ok"}).encode())
                else:
                    self.wfile.write(json.dumps({"status": "success"}).encode())
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"models": [{"name": "eternego-test"}]}).encode())
            def do_DELETE(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{}')
            def log_message(self, *a): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

        outcome = asyncio.run(spec.create(
            name="FeedBot", model="llama3", channel_type="web", channel_credentials={},
        ))
        assert outcome.success is True
        persona_id = outcome.data["persona_id"]
        outcome = asyncio.run(spec.find(persona_id))
        persona = outcome.data["persona"]

        data = json.dumps([
            {"chat_messages": [
                {"sender": "human", "text": "I like Python"},
                {"sender": "assistant", "text": "Great choice"},
            ]}
        ])
        outcome = asyncio.run(spec.feed(persona, data, "claude"))
        assert outcome.success is True, f"Feed failed: {outcome.message}"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


