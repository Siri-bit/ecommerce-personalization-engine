"""
FastAPI service for the Ecommerce Personalization Rules Engine.

Endpoints:
  GET  /health              -> liveness check
  GET  /sessions/mock       -> pre-built mock sessions covering all 5 states
  POST /classify            -> classify a single Session
  POST /simulate            -> stateful: append events to an in-memory session
                                and re-classify (this powers the live simulator UI)
  DELETE /simulate/{id}     -> reset a simulated session
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import Session, Event, Classification
from app.mock_data import get_mock_sessions
from app.features import extract_features
from app.classifier import classify_session, ClassificationError

app = FastAPI(title="Ecommerce Personalization Rules Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for the live simulator (fine for a demo/assignment; would be
# Redis or a DB table in production).
_simulated_sessions: dict[str, Session] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/sessions/mock", response_model=list[Session])
def sessions_mock():
    return get_mock_sessions()


@app.post("/classify", response_model=Classification)
def classify(session: Session):
    features = extract_features(session)
    try:
        return classify_session(session.session_id, features)
    except ClassificationError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/simulate/{session_id}/event")
def simulate_add_event(session_id: str, event: Event):
    """Append one event to a simulated session and return the updated classification.
    This is the endpoint the live simulator frontend calls on every button click."""
    session = _simulated_sessions.get(session_id) or Session(session_id=session_id)
    session.events.append(event)
    _simulated_sessions[session_id] = session

    features = extract_features(session)
    try:
        classification = classify_session(session_id, features)
    except ClassificationError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"features": features, "classification": classification}


@app.delete("/simulate/{session_id}")
def simulate_reset(session_id: str):
    _simulated_sessions.pop(session_id, None)
    return {"reset": True, "session_id": session_id}
