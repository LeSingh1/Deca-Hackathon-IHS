"""Per-service live/mock status for the header chips. One env var flips each service."""
from __future__ import annotations

from .channels import twilio
from .executor.actions import stripe_mode
from .llm.client import PROVIDERS


def services() -> dict[str, str]:
    return {
        "claude": "live" if PROVIDERS["anthropic"].available() else "mock",       # ANTHROPIC_API_KEY
        "stripe": stripe_mode(),                                                  # STRIPE_SECRET_KEY (test only)
        "twilio": twilio.mode(),                                                  # TWILIO_* (3 vars)
    }
