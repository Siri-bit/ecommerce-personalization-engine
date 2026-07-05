
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.classifier import classify_session, ClassificationError
from app.models import Features


def _features():
    return Features(
        distinct_pdp_views=1, collection_views=0, searches=0, filters_applied=0,
        cart_adds=1, cart_removes=0, coupon_lookups=0, checkout_started=True,
        checkout_abandoned=True, purchased=False, session_duration_minutes=7.0,
        is_returning_user=False, past_purchase_count=0,
        event_sequence_summary="page_view_pdp -> add_to_cart -> checkout_start -> checkout_abandon",
    )


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeChoice:
    def __init__(self, content):
        self.message = _FakeMessage(content)


class _FakeChatResponse:
    def __init__(self, content):
        self.choices = [_FakeChoice(content)]


class _FakeCompletions:
    def __init__(self, responses):
        self._responses = list(responses)

    def create(self, **kwargs):
        return _FakeChatResponse(self._responses.pop(0))


class _FakeChat:
    def __init__(self, responses):
        self.completions = _FakeCompletions(responses)


class _FakeClient:
    def __init__(self, responses):
        self.chat = _FakeChat(responses)


VALID_JSON = json.dumps({
    "state": "cart_abandoner",
    "confidence": 0.85,
    "evidence": ["added to cart", "checkout started then abandoned"],
    "recommended_action": "Send a cart-recovery email with a limited-time incentive",
    "reasoning": "Session shows clear purchase intent that stalled at checkout.",
})


def test_classify_succeeds_on_first_valid_response():
    client = _FakeClient([VALID_JSON])
    result = classify_session("s_test", _features(), client=client)
    assert result.state == "cart_abandoner"
    assert result.confidence == 0.85


def test_classify_self_corrects_after_malformed_first_response():
    malformed = "not valid json at all"
    client = _FakeClient([malformed, VALID_JSON])
    result = classify_session("s_test", _features(), client=client)
    assert result.state == "cart_abandoner"


def test_classify_raises_after_two_failed_attempts():
    client = _FakeClient(["still broken", "still broken again"])
    try:
        classify_session("s_test", _features(), client=client)
        assert False, "expected ClassificationError"
    except ClassificationError:
        pass
