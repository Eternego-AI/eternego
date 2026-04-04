from application.platform.processes import on_separate_process_async


async def test_migrate_restores_persona_from_diary():
    def isolated():
        import asyncio
        import os
        import json
        import tempfile
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.business import persona as spec
        from application.core import agents, gateways, paths
        from application.platform import ollama

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
        
        outcome = asyncio.run(spec.create(name="MigrateMe", model="llama3", channel_type="web", channel_credentials={}))
        assert outcome.success is True
        persona_id = outcome.data["persona_id"]
        phrase = outcome.data["recovery_phrase"]

        # 2. Write diary (already done during create, but let's do it explicitly)
        outcome = asyncio.run(spec.find(persona_id))
        persona = outcome.data["persona"]
        outcome = asyncio.run(spec.write_diary(persona))
        assert outcome.success is True

        # 3. Get diary file path
        diary_file = paths.diary(persona_id) / f"{persona_id}.diary"
        assert diary_file.exists(), f"Diary file not found at {diary_file}"

        # 4. Delete persona
        outcome = asyncio.run(spec.delete(persona))
        assert outcome.success is True

        # 5. Migrate using diary and recovery phrase
        outcome = asyncio.run(spec.migrate(str(diary_file), phrase, "llama3"))
    
        assert outcome.success is True, f"Migrate failed: {outcome.message}"
        assert "persona_id" in outcome.data
        assert outcome.data["name"] == "MigrateMe"

    code, error = await on_separate_process_async(isolated)
    assert code == 0, error

