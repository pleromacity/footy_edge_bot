import importlib
import sys

import pytest


def test_config_requires_environment_secrets(monkeypatch):
    """The app should fail fast if API credentials are missing instead of
    silently using hardcoded values committed to source control."""
    monkeypatch.delenv("API_FOOTBALL_KEY", raising=False)
    monkeypatch.delenv("ODDS_API_KEY", raising=False)
    sys.modules.pop("config", None)

    with pytest.raises(RuntimeError, match="API_FOOTBALL_KEY|ODDS_API_KEY"):
        importlib.import_module("config")
