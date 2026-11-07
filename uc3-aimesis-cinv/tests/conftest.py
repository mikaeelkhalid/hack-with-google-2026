"""Pytest configuration for Almesis Copilot (uc3-aimesis-cinv)."""

from __future__ import annotations

from dotenv import load_dotenv
import pytest

load_dotenv()


@pytest.fixture(autouse=True)
def _default_allow_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enables ALLOW_UNVERIFIED=1 by default in tests unless explicitly unset by a test."""
    monkeypatch.setenv("ALLOW_UNVERIFIED", "1")

