"""
These tests deliberately require NO API key -- the feature extraction layer
is pure and deterministic, which is the whole point of separating it from
the LLM call. Run with: pytest tests/
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.mock_data import get_mock_sessions
from app.features import extract_features


def _session(sid):
    return next(s for s in get_mock_sessions() if s.session_id == sid)


def test_browser_has_no_cart_activity():
    f = extract_features(_session("s_browser_01"))
    assert f.cart_adds == 0
    assert f.purchased is False


def test_comparer_has_multiple_pdp_views_no_cart():
    f = extract_features(_session("s_comparer_01"))
    assert f.distinct_pdp_views >= 3
    assert f.cart_adds == 0


def test_discount_seeker_has_coupon_lookups():
    f = extract_features(_session("s_discount_01"))
    assert f.coupon_lookups >= 2


def test_cart_abandoner_started_but_did_not_purchase():
    f = extract_features(_session("s_abandoner_01"))
    assert f.checkout_started is True
    assert f.checkout_abandoned is True
    assert f.purchased is False


def test_loyal_customer_purchased_and_is_returning():
    f = extract_features(_session("s_loyal_01"))
    assert f.purchased is True
    assert f.is_returning_user is True
    assert f.past_purchase_count == 4


def test_distinct_pdp_views_deduplicates_repeated_views():
    # s_comparer_01 views p_201 twice -- distinct count should not double-count
    f = extract_features(_session("s_comparer_01"))
    assert f.distinct_pdp_views == 3  # p_201, p_202, p_203
