"""
Deterministic feature extraction: raw events -> structured Features.

This layer never calls an LLM. It exists so that:
1. The classification is auditable -- you can unit test this in isolation
   (see tests/test_features.py) without touching an API key.
2. The LLM downstream is grounded in counted facts, not asked to "read"
   a raw event log and infer numbers, which is where hallucination creeps in.
"""
from app.models import Session, Features, EventType


def extract_features(session: Session) -> Features:
    events = session.events
    counts = {et: 0 for et in EventType}
    for e in events:
        counts[e.type] += 1

    distinct_pdps = len({e.target for e in events if e.type == EventType.PAGE_VIEW_PDP})

    duration = 0.0
    if len(events) >= 2:
        duration = (events[-1].ts - events[0].ts).total_seconds() / 60.0

    summary_parts = [f"{e.type.value}" + (f"({e.target})" if e.target else "") for e in events]

    return Features(
        distinct_pdp_views=distinct_pdps,
        collection_views=counts[EventType.PAGE_VIEW_COLLECTION],
        searches=counts[EventType.SEARCH],
        filters_applied=counts[EventType.FILTER_APPLIED],
        cart_adds=counts[EventType.ADD_TO_CART],
        cart_removes=counts[EventType.REMOVE_FROM_CART],
        coupon_lookups=counts[EventType.COUPON_LOOKUP],
        checkout_started=counts[EventType.CHECKOUT_START] > 0,
        checkout_abandoned=counts[EventType.CHECKOUT_ABANDON] > 0,
        purchased=counts[EventType.PURCHASE] > 0,
        session_duration_minutes=round(duration, 2),
        is_returning_user=session.user_is_returning,
        past_purchase_count=session.past_purchase_count,
        event_sequence_summary=" -> ".join(summary_parts) if summary_parts else "(no events)",
    )
