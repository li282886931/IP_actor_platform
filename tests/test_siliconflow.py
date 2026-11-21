"""SiliconFlow protocol, authenticated generation and failure boundaries."""
import json

import pytest
import requests

from app.models import AIGeneration
from test_ai_user_isolation import ai_client, login
from test_main import llm_integration


@pytest.fixture
def siliconflow(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "siliconflow")
    monkeypatch.setenv("SILICONFLOW_API_KEY", "test-private-key")
    monkeypatch.setenv("SILICONFLOW_MODEL", "Qwen/Qwen3.5-35B-A3B")
    monkeypatch.setenv("SILICONFLOW_MAX_TOKENS", "8192")
    monkeypatch.setenv("SILICONFLOW_THINKING_BUDGET", "2048")
    monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://unused-local/v1/chat/completions")


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
def test_siliconflow_authenticated_generation_and_clean_persistence(ai_client, siliconflow, monkeypatch, route):
    client, sessions, cache = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    content = "## 传播定位\n以已核验资料编写方案。"
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "<think>隐藏分析</think>" + content,
                                             "reasoning_content": "内部推理"}}]}

        def iter_lines(self, decode_unicode=False):
            assert decode_unicode is False
            for delta in ({"reasoning_content": "内部推理"}, {"content": "<think>隐藏分析</think>" + content}):
                yield ("data: " + json.dumps({"choices": [{"delta": delta}]}, ensure_ascii=False)).encode()
            yield b"data: [DONE]"

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return Response()

    monkeypatch.setattr(llm_integration.requests, "post", post)
    payload = {"type": "poster", "generation_nonce": "cloud-request"}
    response = client.post(route, headers=headers, json=payload)
    assert response.status_code == 200
    if route.endswith("/stream"):
        events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
        assert next(event["result"] for event in events if event["event"] == "final") == content
        assert "本地模型" not in response.text
    else:
        assert response.json()["data"]["result"] == content
    assert "内部推理" not in response.text and "隐藏分析" not in response.text
    url, kwargs = calls[0]
    assert url == "https://api.siliconflow.cn/v1/chat/completions"
    assert kwargs["headers"]["Authorization"] == "Bearer test-private-key"
    assert kwargs["timeout"] == 300
    assert kwargs["json"]["model"] == "Qwen/Qwen3.5-35B-A3B"
    assert kwargs["json"]["enable_thinking"] is True
    prompt = kwargs["json"]["messages"][0]["content"]
    assert not prompt.startswith("/no_think")
    assert "可以在模型 reasoning_content 中组织分析过程" in prompt
    assert kwargs["json"]["max_tokens"] == 8192
    assert kwargs["json"]["thinking_budget"] == 2048
    assert not {"seed", "presence_penalty", "chat_template_kwargs",
                "temperature", "top_p", "frequency_penalty"} & kwargs["json"].keys()
    assert kwargs.get("stream", False) == route.endswith("/stream")
    with sessions() as db:
        assert db.query(AIGeneration).one().result == content
    assert len(cache) == 1
    repeat = client.post(route, headers=headers, json=payload)
    assert repeat.status_code == 200 and "cache_hit" in repeat.text
    assert len(calls) == 1
    monkeypatch.setenv("SILICONFLOW_MODEL", "Qwen/Qwen3-14B")
    assert client.post(route, headers=headers, json=payload).status_code == 200
    assert len(calls) == 2, "Changing models must not reuse a different model's cached result"


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
@pytest.mark.parametrize("field,value", [
    ("SILICONFLOW_API_KEY", ""),
    ("SILICONFLOW_MODEL", ""),
    ("SILICONFLOW_BASE_URL", "http://api.siliconflow.cn/v1"),
    ("SILICONFLOW_BASE_URL", "https://user:password@api.siliconflow.cn/v1"),
    ("LLM_PROVIDER", "misspelled-provider"),
])
def test_invalid_cloud_configuration_fails_before_outbound_request(ai_client, siliconflow, monkeypatch, route, field, value):
    client, sessions, cache = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    monkeypatch.setenv(field, value)
    calls = []
    monkeypatch.setattr(llm_integration.requests, "post", lambda *args, **kwargs: calls.append(args))
    response = client.post(route, headers=headers, json={"type": "poster"})
    assert response.status_code == 503
    assert not calls and not cache
    with sessions() as db:
        assert db.query(AIGeneration).count() == 0


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
@pytest.mark.parametrize("failure", ["http", "timeout", "empty"])
def test_cloud_failure_never_saves_fallback_or_leaks_key(ai_client, siliconflow, monkeypatch, capsys, route, failure):
    client, sessions, cache = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    calls = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            if failure == "http":
                raise requests.HTTPError("upstream detail test-private-key")

        def json(self):
            return {"choices": []}

        def iter_lines(self, **kwargs):
            yield b"data: [DONE]"

    def post(*args, **kwargs):
        calls.append(args)
        if failure == "timeout":
            raise requests.Timeout("test-private-key")
        return Response()

    monkeypatch.setattr(llm_integration.requests, "post", post)
    response = client.post(route, headers=headers, json={"type": "poster"})
    if route.endswith("/stream"):
        assert response.status_code == 200
        assert '"event": "error"' in response.text and '"event": "final"' not in response.text
    else:
        assert response.status_code == 502
    assert len(calls) == 1 and not cache
    assert "test-private-key" not in response.text + capsys.readouterr().out
    with sessions() as db:
        assert db.query(AIGeneration).count() == 0


@pytest.mark.parametrize("ending", ["disconnect", "error"])
def test_incomplete_cloud_stream_does_not_persist_partial_result(ai_client, siliconflow, monkeypatch, ending):
    client, sessions, cache = ai_client
    headers, _ = login(client, monkeypatch, "b_user")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self, **kwargs):
            yield 'data: {"choices":[{"delta":{"content":"## 传播定位\\n部分结果"}}]}'.encode()
            if ending == "error":
                yield b'data: {"error":{"message":"private upstream error"}}'
            # No [DONE]: this must not be treated as a successful result.

    monkeypatch.setattr(llm_integration.requests, "post", lambda *args, **kwargs: Response())
    response = client.post("/ai/generate/stream", headers=headers, json={"type": "poster"})
    assert '"event": "error"' in response.text
    assert '"event": "final"' not in response.text and "private upstream error" not in response.text
    assert not cache
    with sessions() as db:
        assert db.query(AIGeneration).count() == 0


def test_docker_passes_cloud_settings_without_bundling_secret(tmp_path):
    from pathlib import Path
    import shutil
    import subprocess
    from test_deployment import deployment_env

    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is needed to render Compose")
    root = Path(__file__).resolve().parents[1]
    env_file = tmp_path / "deployment.env"
    env_file.write_text("\n".join(f"{key}={value}" for key, value in deployment_env().items()))
    result = subprocess.run(
        ["docker", "compose", "--env-file", str(env_file), "-f", str(root / "docker-compose.yml"),
         "config", "--format", "json"], capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    environment = json.loads(result.stdout)["services"]["backend"]["environment"]
    assert environment["LLM_PROVIDER"] == "siliconflow"
    assert environment["SILICONFLOW_API_KEY"] == ""
    assert environment["SILICONFLOW_BASE_URL"] == "https://api.siliconflow.cn/v1"
    assert environment["SILICONFLOW_MODEL"] == "Qwen/Qwen3.5-35B-A3B"
    assert environment["SILICONFLOW_MAX_TOKENS"] == "8192"
    assert environment["SILICONFLOW_THINKING_BUDGET"] == "2048"


def test_default_configuration_selects_new_cloud_model(monkeypatch):
    import runpy
    from pathlib import Path

    for name in ("LLM_PROVIDER", "SILICONFLOW_MODEL", "SILICONFLOW_MAX_TOKENS", "SILICONFLOW_THINKING_BUDGET"):
        monkeypatch.delenv(name, raising=False)
    values = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app/config/__init__.py"))
    assert values["LLM_PROVIDER"] == "siliconflow"
    assert values["SILICONFLOW_MODEL"] == "Qwen/Qwen3.5-35B-A3B"
    assert values["SILICONFLOW_MAX_TOKENS"] == 8192
    assert values["SILICONFLOW_THINKING_BUDGET"] == 2048


def test_local_generation_retains_local_sampling_parameters():
    connection = llm_integration.GenerationConnection("llama-server", "http://local", "local-model")
    body = llm_integration.generation_request(connection, "正文", 42, 800)["json"]
    assert body["temperature"] == 0.95
    assert body["top_p"] == 0.92
    assert body["frequency_penalty"] == 0.35
    assert body["seed"] == 42
    assert body["max_tokens"] == 800


def test_cloud_prompt_requires_final_heading_and_unverified_claim_boundaries():
    from app.schemas import AIGenerateIn
    prompt = llm_integration.build_ai_generation_prompt(AIGenerateIn(type="poster"), "batch", allow_thinking=True)
    assert "# 演出宣发方案" in prompt
    assert "不得写成既定事实" in prompt
    assert "余票告急" in prompt


@pytest.mark.parametrize("route", ["/ai/generate", "/ai/generate/stream"])
def test_cloud_stream_skips_analysis_preamble_before_final_heading(ai_client, siliconflow, monkeypatch, route):
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content":
                "传播定位分析：内部规划。\n最终 Content 将输出方案。\ncontent\n"
                "# 演出宣发方案\n## 传播定位\n已核验资料。"}}]}

        def iter_lines(self, **kwargs):
            for content in ["传播定位分析：内部规划。\n最终 Content 将输出方案。\ncontent\n",
                            "# 演出宣发方案\n## 传播定位\n已核验资料。"]:
                yield ("data: " + json.dumps({"choices": [{"delta": {"content": content}}]})).encode()
            yield b"data: [DONE]"

    monkeypatch.setattr(llm_integration.requests, "post", lambda *a, **kw: Response())
    response = client.post(route, headers=headers, json={"type": "poster"})
    assert "内部规划" not in response.text
    assert "最终 Content" not in response.text
    with sessions() as db:
        assert db.query(AIGeneration).one().result.startswith("# 演出宣发方案")
