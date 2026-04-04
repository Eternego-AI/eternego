from application.platform.processes import on_separate_process_async


async def test_ready_succeeds_when_engine_serving():
    def isolated():
        import os
        import json
        import asyncio
        import tempfile
        import threading
        import subprocess
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.business import environment
        from application.core import agents, gateways
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
        subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                if self.path == "/api/chat":
                    self.wfile.write(json.dumps({"message": {"content": "ok"}}).encode())
                elif self.path == "/api/generate":
                    self.wfile.write(json.dumps({"response": "ok"}).encode())
                else:
                    self.wfile.write(json.dumps({"status": "success"}).encode())
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"models": [{"name": "llama3"}]}).encode())
            def log_message(self, *a): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

        result = asyncio.run(environment.ready())
        assert result.success is True

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
