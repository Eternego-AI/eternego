from application.platform.hugging_face import id_for, ids


def test_id_for_exact_match():
    assert id_for("qwen2.5:7b") == "Qwen/Qwen2.5-7B-Instruct"
    assert id_for("llama3.2:3b") == "meta-llama/Llama-3.2-3B-Instruct"


def test_id_for_strips_quantization_suffix():
    assert id_for("qwen2.5:7b-q4_k_m") == "Qwen/Qwen2.5-7B-Instruct"


def test_id_for_returns_none_for_unknown():
    assert id_for("nonexistent:99b") is None


def test_ids_returns_full_map():
    result = ids()
    assert isinstance(result, dict)
    assert len(result) > 10
    assert "qwen2.5:7b" in result
