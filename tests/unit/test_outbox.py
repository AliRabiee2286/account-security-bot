from app.core.outbox_dispatch import backoff


def test_backoff_is_bounded():
    assert backoff(1).seconds == 1
    assert backoff(5).seconds == 16
    assert backoff(20).seconds == 300
