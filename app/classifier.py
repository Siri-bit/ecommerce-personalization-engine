

"""
LLM-backed classification layer.

Uses the Groq API (OpenAI-compatible SDK) to classify shopper behavior.

The classifier sends extracted session features to the LLM, validates the
structured JSON response using Pydantic, and retries once if the response
is malformed.
"""


import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.models import Features, Classification

load_dotenv()

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = """You are a deterministic ecommerce shopper classification engine.

You will be given EXTRACTED FEATURES from a single browsing session -- never raw events.
Classify the shopper into EXACTLY ONE of these states:
- browser: low signal, casual viewing, no strong intent markers
- comparer: multiple distinct product views and/or filters, no cart action
- discount_seeker: coupon lookups and/or price-focused filtering present
- cart_abandoner: added to cart and/or started checkout, but did not purchase
- loyal_customer: returning user with purchase history, especially if they purchased this session

RULES:
1. Base your answer ONLY on the features given. Do not invent behavior not present in the data.
2. If the evidence is genuinely mixed or thin, lower your confidence score accordingly (below 0.6).
   Do not force high confidence just to sound decisive.
3. "evidence" must list only facts drawn directly from the features you were given.
4. Return ONLY valid JSON, no markdown fences, no preamble, matching exactly this shape:
{
  "state": "<one of the five states above>",
  "confidence": <float 0.0-1.0>,
  "evidence": ["<fact 1>", "<fact 2>", ...],
  "recommended_action": "<one concrete, specific site action or nudge>",
  "reasoning": "<2-3 sentences explaining the call>"
}
"""


class ClassificationError(Exception):
    pass


# def _get_client():
#     """Returns a configured genai.Client. Kept as a factory function (rather
#     than instantiated at import time) so tests can inject a fake object
#     without touching real API config or spending a real request."""
#     return genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))



def _get_client():
    return OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )


def _call_model(client, features, session_id, retry_note=""):
    user_content = f"""SESSION_ID: {session_id}
FEATURES: {features.model_dump_json()}
{retry_note}
"""

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            },
            {
                "role": "user",
                "content": user_content
            }
        ]
    )

    return response.choices[0].message.content


def classify_session(session_id: str, features: Features, client=None) -> Classification:
    client = client or _get_client()  

    raw = _call_model(client, features, session_id)
    try:
        data = json.loads(raw)
        data["session_id"] = session_id
        return Classification(**data)
    except Exception as first_err:
        # Self-correcting retry: feed the error back to the model once.
        retry_note = (
            f"\nYour previous response failed validation with error: {first_err}\n"
            f"Previous response was: {raw}\n"
            "Return ONLY corrected valid JSON matching the required shape exactly."
        )
        raw_retry = _call_model(client, features, session_id, retry_note=retry_note)
        try:
            data = json.loads(raw_retry)
            data["session_id"] = session_id
            return Classification(**data)
        except Exception as second_err:
            raise ClassificationError(
                f"Classification failed after retry. First error: {first_err}. "
                f"Second error: {second_err}. Raw output: {raw_retry}"
            )
