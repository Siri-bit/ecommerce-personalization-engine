# Ecommerce Personalization Engine

An LLM-powered mini-engine that classifies live shopper sessions into
behavioral states (`browser`, `comparer`, `discount_seeker`, `cart_abandoner`,
`loyal_customer`) and recommends a concrete site action for each — with a
live simulator to demo classification updating in real time.

Built as a take-home assignment (Option C).
The goal is to infer shopper intent from browsing behavior and recommend the
next best action for personalization using a combination of deterministic
feature extraction and LLM reasoning.
This README documents *why*
things are built the way they are, not just what they do — the reasoning
is the actual deliverable.

**LLM provider:** Groq (`llama-3.3-70b-versatile`) using the OpenAI-compatible SDK.
The architecture is provider-agnostic by design—`classify_session()` accepts a
client object, so swapping to another model (Gemini, Claude, GPT, or a local
LLM) only requires changing the client initialization rather than rewriting the
classification logic.
## Quick start

```bash
cp .env.example .env         # add your GROQ_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Then open `frontend/index.html` directly in a browser (no build step) and
start clicking events. It talks to `http://localhost:8000` by default.

Or via Docker:
```bash
docker build -t epe . && docker run -p 8000:8000 --env-file .env epe
```

Run the tests (no API key required — see "Why tests don't need a key" below):
```bash
pytest tests/
```

## Architecture

```
Events (raw)  →  Features (deterministic)  →  LLM Classifier (structured)  →  Classification
                                                     ↑
                                          self-corrects on invalid JSON
```

Three deliberately separated stages:

1. **`app/features.py` — deterministic extraction.** Counts distinct PDP
   views, cart adds/removes, coupon lookups, checkout state, session
   duration, and returning-user signal. Pure Python, no LLM call, fully
   unit-testable.
2. **`app/classifier.py` — LLM classification.** The model receives *only*
   the extracted features (never raw events), and is explicitly instructed
   not to invent behavior that isn't in the data. It returns strict JSON
   validated against a Pydantic schema. If validation fails, the error is
   fed back to the model once for a self-correcting retry before giving up.
3. **`app/main.py` — API layer.** A stateless `/classify` endpoint for
   one-shot session scoring, and a stateful `/simulate/{id}/event` endpoint
   that powers the live demo: each click appends one event and re-runs the
   full pipeline.

## Key design decisions (and why)

**Why extract features before calling the LLM, instead of just describing
the whole event log in the prompt?**
Two reasons. First, grounding: if the model only sees counted facts ("3
distinct PDP views, 0 cart adds"), it physically cannot claim the shopper
added something to cart that they didn't — the hallucination surface
shrinks to near zero. Second, testability: the feature layer is pure and
deterministic, so `tests/test_features.py` can assert exact behavior with
zero flakiness and zero API cost. The LLM is only asked to do the one thing
it's actually good at — reasoning over a small set of grounded signals to
produce a judgment call and a plain-English explanation.

**Why confidence scores instead of just a label?**
A rules engine that always sounds certain is a rules engine nobody trusts
in production. The prompt explicitly instructs the model to lower confidence
when evidence is thin or mixed (see `s_ambiguous_01` in `mock_data.py` — a
returning user browsing like a first-timer). A real personalization system
would use this to gate aggressive actions (e.g. only show a discount popup
above 0.7 confidence) rather than firing on every guess.

**Why a self-correcting retry instead of just failing on bad JSON?**
LLMs occasionally wrap JSON in prose or markdown fences despite instructions.
Rather than crash the request, the classifier feeds the validation error
back to the model once and asks it to correct itself. This mirrors the
same pattern used in the resume-parsing pipeline in a related project —
retry-with-error-context is more robust than retry-with-identical-prompt.

**Why a plain HTML/JS simulator instead of React?**
Currently this is an assignment, i would implement this further in upcoming days, the simulator's job is to *demo the reasoning
loop*, not showcase frontend framework skill (the backend already does that
job). A single file with zero build step means a reviewer can open it
immediately without `npm install`. The classification logic is 100% backend
— the frontend is intentionally a thin, disposable shell.

**Why does the test suite not require an API key?**
`tests/test_features.py` tests the pure extraction layer directly.
`tests/test_classifier.py` injects a fake Gemini client (see the
`_FakeClient` classes) to test the retry/validation logic without making
real API calls. This means CI, or a reviewer without your API key, can
still verify the core logic actually works — which matters more for
"code quality" evaluation than a demo that only works on your machine.

## What I'd add with more time

- Persist simulated sessions in Redis instead of an in-memory dict, so the
  demo survives a server restart.
- A confidence-calibration eval: run the classifier against a labeled set
  of ~30 synthetic sessions and measure accuracy vs. confidence correlation.
- Batch classification endpoint for scoring a full session log offline.
- Swap the in-memory mock sessions for a small SQLite fixture so `/sessions/mock`
  and `/simulate` share one persistence layer.

## Bonus requirement: live simulator

`frontend/index.html` — click any event button, watch the classification,
confidence bar, evidence list, and recommended action update in real time
against the live backend. Reset button clears the session to start a new
scenario.

## License

This project was developed as part of a technical assessment and is shared for demonstration purposes.
