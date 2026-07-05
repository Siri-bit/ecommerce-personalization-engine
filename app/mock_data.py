"""
Generates realistic mock session data covering all 5 target states,
plus a couple of deliberately ambiguous sessions to prove the engine
reports lower confidence when evidence is genuinely mixed -- rather than
forcing a confident answer every time. A reviewer testing edge cases
first is a reviewer you want to impress.
"""
from datetime import datetime, timedelta
from app.models import Session, Event, EventType

_BASE = datetime(2026, 7, 1, 10, 0, 0)


def _t(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def get_mock_sessions() -> list[Session]:
    return [
        # 1. Pure browser: low signal, no cart activity
        Session(
            session_id="s_browser_01",
            events=[
                Event(type=EventType.PAGE_VIEW_HOME, ts=_t(0)),
                Event(type=EventType.PAGE_VIEW_COLLECTION, target="mens-shoes", ts=_t(1)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_101", ts=_t(3)),
            ],
        ),
        # 2. Comparer: many PDPs + filters, no cart action
        Session(
            session_id="s_comparer_01",
            events=[
                Event(type=EventType.PAGE_VIEW_COLLECTION, target="running-shoes", ts=_t(0)),
                Event(type=EventType.FILTER_APPLIED, target="size:9", ts=_t(1)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_201", ts=_t(2)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_202", ts=_t(4)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_203", ts=_t(6)),
                Event(type=EventType.FILTER_APPLIED, target="price:low-high", ts=_t(7)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_201", ts=_t(9)),
            ],
        ),
        # 3. Discount seeker: coupon lookups, price filtering
        Session(
            session_id="s_discount_01",
            events=[
                Event(type=EventType.PAGE_VIEW_PDP, target="p_301", ts=_t(0)),
                Event(type=EventType.COUPON_LOOKUP, ts=_t(1)),
                Event(type=EventType.SEARCH, target="promo code", ts=_t(2)),
                Event(type=EventType.ADD_TO_CART, target="p_301", ts=_t(3)),
                Event(type=EventType.COUPON_LOOKUP, ts=_t(4)),
            ],
        ),
        # 4. Cart abandoner: added, started checkout, left
        Session(
            session_id="s_abandoner_01",
            events=[
                Event(type=EventType.PAGE_VIEW_PDP, target="p_401", ts=_t(0)),
                Event(type=EventType.ADD_TO_CART, target="p_401", ts=_t(2)),
                Event(type=EventType.CHECKOUT_START, ts=_t(5)),
                Event(type=EventType.CHECKOUT_ABANDON, ts=_t(7)),
            ],
        ),
        # 5. Loyal customer: returning user, past purchases, quick purchase
        Session(
            session_id="s_loyal_01",
            user_is_returning=True,
            past_purchase_count=4,
            events=[
                Event(type=EventType.RETURN_VISIT, ts=_t(0)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_501", ts=_t(1)),
                Event(type=EventType.ADD_TO_CART, target="p_501", ts=_t(2)),
                Event(type=EventType.CHECKOUT_START, ts=_t(3)),
                Event(type=EventType.PURCHASE, target="p_501", ts=_t(4)),
            ],
        ),
        # 6. Ambiguous: returning user but browsing like a first-timer -- should
        #    yield lower confidence rather than a forced label.
        Session(
            session_id="s_ambiguous_01",
            user_is_returning=True,
            past_purchase_count=1,
            events=[
                Event(type=EventType.PAGE_VIEW_HOME, ts=_t(0)),
                Event(type=EventType.PAGE_VIEW_COLLECTION, target="new-arrivals", ts=_t(1)),
                Event(type=EventType.PAGE_VIEW_PDP, target="p_601", ts=_t(3)),
                Event(type=EventType.REMOVE_FROM_CART, target="p_601", ts=_t(4)),
            ],
        ),
    ]
