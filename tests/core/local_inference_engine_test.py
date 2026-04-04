from application.platform.processes import on_separate_process_async


async def test_get_default_model_returns_first_model():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        result = {}
        async def run():
            result["value"] = await local_inference_engine.get_default_model()
        ollama.assert_call(run=run, response={"models": [{"name": "llama3:latest"}, {"name": "phi4:14b"}]})
        assert result["value"] == "llama3:latest", result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_get_default_model_returns_none_when_no_models():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        result = {}
        async def run():
            result["value"] = await local_inference_engine.get_default_model()
        ollama.assert_call(run=run, response={"models": []})
        assert result["value"] is None, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_pull_sends_correct_model_name():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        def validate(r):
            assert r["path"] == "/api/pull", r["path"]
            assert r["body"]["name"] == "llama3:latest", r["body"]
        ollama.assert_call(
            run=lambda: local_inference_engine.pull("llama3:latest"),
            validate=validate,
            response={"status": "success"},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_register_sends_model_and_base():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        def validate(r):
            assert r["path"] == "/api/create", r["path"]
            assert r["body"]["model"] == "primus-llama3", r["body"]
            assert r["body"]["from"] == "llama3:latest", r["body"]
        ollama.assert_call(
            run=lambda: local_inference_engine.register("primus-llama3", "llama3:latest"),
            validate=validate,
            response={},
        )
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_delete_sends_correct_model():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        result = {}
        async def run():
            result["value"] = await local_inference_engine.delete("llama3:latest")
        def validate(r):
            assert r["path"] == "/api/delete", r["path"]
            assert r["body"]["name"] == "llama3:latest", r["body"]
        ollama.assert_call(run=run, validate=validate, response={})
        assert result["value"] is True, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_check_returns_true_when_model_exists():
    def isolated():
        import json, threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        from application.core import local_inference_engine
        from application.platform import ollama
        import config.inference as cfg

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"models": [{"name": "llama3:latest"}]}).encode())
            def do_POST(self):
                self.rfile.read(int(self.headers.get("Content-Length", 0)))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"response": "hi"}).encode())
            def log_message(self, *a): pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        cfg.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"
        ollama.OLLAMA_BASE_URL = f"http://127.0.0.1:{port}"

        import asyncio
        result = asyncio.run(local_inference_engine.check("llama3:latest"))
        server.shutdown()
        assert result is True, result
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error


async def test_check_returns_false_when_model_not_in_list():
    def isolated():
        from application.platform import ollama
        from application.core import local_inference_engine
        result = {}
        async def run():
            result["value"] = await local_inference_engine.check("nonexistent:model")
        ollama.assert_call(run=run, response={"models": [{"name": "llama3:latest"}]})
        assert result["value"] is False, result["value"]
    code, error = await on_separate_process_async(isolated)
    assert code == 0, error
