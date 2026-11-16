import json

import pytest

from test_ai_user_isolation import ai_client, login
from test_main import llm_integration
from app.models import AIGeneration


@pytest.mark.parametrize("parts,expected", [
    (["## 本地内容方案\n\n", "### 项目定位\n", "以项目资料为依据。\n\n", "### 执行建议\n", "先核验授权后发布。"],
     "## 本地内容方案\n\n### 项目定位\n以项目资料为依据。\n\n### 执行建议\n先核验授权后发布。"),
    (["这是一份以核验资料为依据的正式宣传文案，", "请先确认演出档期与票价，", "再发布音乐现场的完整介绍。"],
     "这是一份以核验资料为依据的正式宣传文案，请先确认演出档期与票价，再发布音乐现场的完整介绍。"),
    (["<thi", "nk>不应展示的内部分析", "</thi", "nk>## 完整内容\n", "请先核验演出资料。"],
     "## 完整内容\n请先核验演出资料。"),
])
def test_stream_preserves_complete_content_and_hides_split_think_tags(ai_client, monkeypatch, parts, expected):
    client, sessions, _ = ai_client
    headers, _ = login(client, monkeypatch, "b_user")
    monkeypatch.setenv("LLAMA_SERVER_URL", "http://127.0.0.1:18080/v1/chat/completions")

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def raise_for_status(self):
            pass

        def iter_lines(self, decode_unicode=False):
            assert decode_unicode is False
            for content in parts:
                yield ("data: " + json.dumps({"choices": [{"delta": {"content": content}}]}, ensure_ascii=False)).encode("utf-8")
            yield b"data: [DONE]"

    monkeypatch.setattr(llm_integration.requests, "post", lambda *args, **kwargs: Response())
    response = client.post("/ai/generate/stream", headers=headers, json={"type": "poster"})
    assert response.status_code == 200
    events = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    assert next(event["result"] for event in events if event["event"] == "final") == expected
    assert "不应展示的内部分析" not in response.text
    with sessions() as db:
        assert db.query(AIGeneration).one().result == expected
