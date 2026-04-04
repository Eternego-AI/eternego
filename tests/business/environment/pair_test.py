from application.platform.processes import on_separate_process_async

async def test_pair_claims_code():
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
        from application.core.data import Channel
        from application.platform import ollama

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
        subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})
        from application.business import persona as spec        

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

        create_result = create_result = asyncio.run(spec.create(
            name="PairBot", model="llama3", channel_type="telegram",
            channel_credentials={"token": "fake"},
        ))
        assert create_result.success is True
        persona_id = create_result.data["persona_id"]
        find_result = asyncio.run(spec.find(persona_id))
        persona = find_result.data["persona"]

        code = agents.pair(persona, Channel(type="telegram", name="12345"))
        result = asyncio.run(environment.pair(code))
        assert result.success is True
        assert "persona_id" in result.data
    
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pair_fails_on_invalid_code():
    def isolated():
        import os
        import asyncio
        import tempfile
        import subprocess
        from application.business import environment
        from application.core import agents, gateways

        tmp = tempfile.mkdtemp()
        os.environ["HOME"] = tmp
        agents._personas.clear()
        gateways._active.clear()
        subprocess.run(["git", "config", "--global", "user.email", "test@test.com"], env={**os.environ, "HOME": tmp})
        subprocess.run(["git", "config", "--global", "user.name", "Test"], env={**os.environ, "HOME": tmp})
        result = asyncio.run(environment.pair("INVALID"))
        assert result.success is False

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
    
