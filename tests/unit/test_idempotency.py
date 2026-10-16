from app.core.idempotency import key


def test_idempotency_stable_and_context_bound():
    assert key("incident", "a", "b") == key("incident", "a", "b")
    assert key("incident", "a", "b") != key("incident", "a", "c")
