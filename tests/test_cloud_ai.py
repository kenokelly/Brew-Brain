"""AI provider switch: Claude API ("cloud") with fallback to Ollama ("local")."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import services.ai as ai


def _cfg(**over):
    cfg = {"ai_provider": "local", "anthropic_api_key": "", "cloud_model": "claude-opus-5"}
    cfg.update(over)
    return lambda k: cfg.get(k)


def _reply(text="Looks healthy.", stop="end_turn"):
    return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="thinking", thinking=""),
                                                      SimpleNamespace(type="text", text=text)])


PAYLOAD = {"model": "phi3:mini", "prompt": "How's my batch?", "system": "You are the Brewmaster.", "stream": False}


def test_local_provider_calls_ollama():
    with patch.object(ai, "get_config", side_effect=_cfg()), \
         patch("services.ai.requests.post") as post, patch("services.ai.cloud_generate") as cloud:
        ai._llm_post("http://ollama:11434/api/generate", PAYLOAD, timeout=5)
    post.assert_called_once()
    cloud.assert_not_called()


def test_cloud_selected_but_no_key_stays_local():
    with patch.object(ai, "get_config", side_effect=_cfg(ai_provider="cloud")), \
         patch("services.ai.requests.post") as post, patch("services.ai.cloud_generate") as cloud:
        ai._llm_post("http://ollama:11434/api/generate", PAYLOAD, timeout=5)
    post.assert_called_once()
    cloud.assert_not_called()


def test_cloud_provider_returns_cloud_reply():
    with patch.object(ai, "get_config", side_effect=_cfg(ai_provider="cloud", anthropic_api_key="sk-test")), \
         patch("services.ai.requests.post") as post, \
         patch("services.ai.cloud_generate", return_value="Fermenting nicely.") as cloud:
        res = ai._llm_post("http://ollama:11434/api/generate", PAYLOAD, timeout=5)
    assert res.status_code == 200
    assert res.json() == {"response": "Fermenting nicely.", "source": "cloud"}
    cloud.assert_called_once_with("You are the Brewmaster.", "How's my batch?")
    post.assert_not_called()


def test_cloud_failure_falls_back_to_local():
    with patch.object(ai, "get_config", side_effect=_cfg(ai_provider="cloud", anthropic_api_key="sk-test")), \
         patch("services.ai.requests.post") as post, \
         patch("services.ai.cloud_generate", side_effect=ConnectionError("offline")):
        ai._llm_post("http://ollama:11434/api/generate", PAYLOAD, timeout=5)
    post.assert_called_once()


def test_chat_reports_cloud_source():
    with patch.object(ai, "get_config", side_effect=_cfg(ai_provider="cloud", anthropic_api_key="sk-test")), \
         patch.object(ai, "build_batch_context", return_value="Current gravity 1.015"), \
         patch("services.ai.cloud_generate", return_value="All good."):
        out = ai.generate_chat_response("How is it?")
    assert out == {"status": "success", "response": "All good.", "source": "cloud"}


# ---------------------------------------------------------------------------
# Per-model request shape
# ---------------------------------------------------------------------------

def _client():
    client = MagicMock()
    client.messages.create.return_value = _reply()
    client.beta.messages.create.return_value = _reply()
    return client


def test_opus_uses_low_effort_and_server_fallback():
    client = _client()
    with patch.object(ai, "get_config", side_effect=_cfg(anthropic_api_key="sk-test")), \
         patch("anthropic.Anthropic", return_value=client):
        assert ai.cloud_generate("sys", "hi", model="claude-opus-5") == "Looks healthy."
    kw = client.beta.messages.create.call_args.kwargs
    assert kw["model"] == "claude-opus-5"
    assert kw["output_config"] == {"effort": "low"}
    assert kw["fallbacks"] == "default"
    assert kw["betas"] == ["server-side-fallback-2026-07-01"]
    client.messages.create.assert_not_called()


def test_haiku_sends_no_effort():
    """effort errors on Haiku 4.5."""
    client = _client()
    with patch.object(ai, "get_config", side_effect=_cfg(anthropic_api_key="sk-test")), \
         patch("anthropic.Anthropic", return_value=client):
        ai.cloud_generate("sys", "hi", model="claude-haiku-4-5")
    kw = client.messages.create.call_args.kwargs
    assert kw["model"] == "claude-haiku-4-5" and "output_config" not in kw


def test_sonnet_uses_low_effort():
    client = _client()
    with patch.object(ai, "get_config", side_effect=_cfg(anthropic_api_key="sk-test")), \
         patch("anthropic.Anthropic", return_value=client):
        ai.cloud_generate("sys", "hi", model="claude-sonnet-5")
    assert client.messages.create.call_args.kwargs["output_config"] == {"effort": "low"}


def test_unknown_model_falls_back_to_default():
    client = _client()
    with patch.object(ai, "get_config", side_effect=_cfg(anthropic_api_key="sk-test")), \
         patch("anthropic.Anthropic", return_value=client):
        ai.cloud_generate("sys", "hi", model="gpt-5")
    assert client.beta.messages.create.call_args.kwargs["model"] == "claude-opus-5"


def test_refusal_raises_so_local_fallback_runs():
    client = _client()
    client.beta.messages.create.return_value = _reply(text="", stop="refusal")
    with patch.object(ai, "get_config", side_effect=_cfg(anthropic_api_key="sk-test")), \
         patch("anthropic.Anthropic", return_value=client):
        with pytest.raises(RuntimeError):
            ai.cloud_generate("sys", "hi", model="claude-opus-5")
