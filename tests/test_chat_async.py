"""Brewmaster chat runs as a background job; advice is cached."""

from unittest.mock import MagicMock, patch

import services.ai as ai


def test_advice_served_from_cache_without_calling_ollama():
    cached = {"status": "success", "advice": "Raise to 20C for a diacetyl rest.", "source": "ollama"}
    with patch.object(ai.cache, "get", return_value=cached), patch("services.ai.requests.post") as post:
        assert ai.get_proactive_advice() == cached
    post.assert_not_called()


def test_advice_single_flight_returns_pending_when_locked():
    redis = MagicMock()
    redis.set.return_value = False  # another request holds the lock
    with patch.object(ai.cache, "get", return_value=None), \
         patch.object(ai.cache, "redis_client", redis), \
         patch("services.ai.requests.post") as post:
        result = ai.get_proactive_advice()
    assert result["source"] == "pending"
    post.assert_not_called()


def _client():
    from flask import Flask
    from api.ai import ai_bp
    app = Flask(__name__)
    app.register_blueprint(ai_bp, url_prefix="/api/ai")
    return app.test_client()


def test_chat_enqueues_and_trims_history():
    task = MagicMock(id="abc123")
    with patch("services.tasks.run_chat_task.delay", return_value=task) as delay:
        res = _client().post("/api/ai/chat", json={"message": "What's brewing?", "history": [{"role": "user", "content": str(i)} for i in range(25)]})
    assert res.status_code == 202
    assert res.get_json()["data"] == {"status": "queued", "task_id": "abc123"}
    msg, history = delay.call_args.args
    assert msg == "What's brewing?" and len(history) == 10


def test_chat_rejects_empty_and_oversized():
    c = _client()
    assert c.post("/api/ai/chat", json={}).status_code == 400
    assert c.post("/api/ai/chat", json={"message": "x" * 2001}).status_code == 400


def test_chat_status_states():
    c = _client()
    for state, expected in [("PENDING", "queued"), ("STARTED", "thinking")]:
        with patch("celery.result.AsyncResult", return_value=MagicMock(state=state)):
            assert c.get("/api/ai/chat/status/t1").get_json()["data"]["status"] == expected
    done = MagicMock(state="SUCCESS")
    done.get.return_value = {"status": "success", "response": "Looks healthy."}
    with patch("celery.result.AsyncResult", return_value=done):
        assert c.get("/api/ai/chat/status/t1").get_json()["data"]["response"] == "Looks healthy."
