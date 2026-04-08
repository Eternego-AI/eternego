from application.platform.processes import on_separate_process_async


async def test_delete_succeeds():
    def isolated():
        import asyncio
        import os
        import json
        import tempfile
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.business import persona as spec
        from application.core import agents, gateways
        from application.platform import ollama
        from application.core.data import Model, Channel
        from application.platform import OS
        OS._secret_cache_only = True

        tmp = tempfile.mkdtemp()
        os.environ["ETERNEGO_HOME"] = tmp
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
            name="DeleteMe", thinking=Model(name="llama3"), channel=Channel(type="web", credentials={}),
        ))
        assert outcome.success, outcome.message
        outcome = asyncio.run(spec.find(outcome.data["persona_id"]))
        outcome = asyncio.run(spec.delete(outcome.data["persona"]))
        assert outcome.success, outcome.message

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
