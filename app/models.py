"""
Core data contracts for the Ecommerce Personalization Rules Engine.

Design note: We deliberately separate raw Events -> Features -> Classification
into three distinct, strongly-typed stages. This is the same discipline used
in the AI Job Copilot's resume-parsing pipeline: never let the LLM see raw,
unstructured input when a deterministic layer can extract grounded signal first.
It keeps the model honest (it can't invent behavior that isn't in the features)
and makes the whole pipeline debuggable stage-by-stage.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    PAGE_VIEW_HOME = "page_view_home"
    PAGE_VIEW_COLLECTION = "page_view_collection"
    PAGE_VIEW_PDP = "page_view_pdp"
    SEARCH = "search"
    FILTER_APPLIED = "filter_applied"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    COUPON_LOOKUP = "coupon_lookup"
    CHECKOUT_START = "checkout_start"
    CHECKOUT_ABANDON = "checkout_abandon"
    PURCHASE = "purchase"
    RETURN_VISIT = "return_visit"


class Event(BaseModel):
    type: EventType
    target: Optional[str] = None      # e.g. product_id, collection_slug, search query
    ts: datetime


class Session(BaseModel):
    session_id: str
    user_is_returning: bool = False
    past_purchase_count: int = 0
    events: list[Event] = Field(default_factory=list)


class Features(BaseModel):
    """Deterministic, auditable signals extracted from a session.
    This is what actually gets sent to the LLM -- never raw events."""
    distinct_pdp_views: int
    collection_views: int
    searches: int
    filters_applied: int
    cart_adds: int
    cart_removes: int
    coupon_lookups: int
    checkout_started: bool
    checkout_abandoned: bool
    purchased: bool
    session_duration_minutes: float
    is_returning_user: bool
    past_purchase_count: int
    event_sequence_summary: str  # short human-readable trace for LLM context


class ShopperState(str, Enum):
    BROWSER = "browser"
    COMPARER = "comparer"
    DISCOUNT_SEEKER = "discount_seeker"
    CART_ABANDONER = "cart_abandoner"
    LOYAL_CUSTOMER = "loyal_customer"


class Classification(BaseModel):
    session_id: str
    state: ShopperState
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    recommended_action: str
    reasoning: str
