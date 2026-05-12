"""Tests for the tiered ModelRouter."""

from hardwise.agent.router import ModelRouter


def test_select_fast_reads_fast_env_var() -> None:
    env = {
        "HARDWISE_MODEL_FAST": "mimo-v2.5-lite",
        "HARDWISE_MODEL_NORMAL": "mimo-v2.5",
        "HARDWISE_MODEL_DEEP": "mimo-v2.5-pro",
    }
    assert ModelRouter(env).select("fast") == "mimo-v2.5-lite"


def test_select_normal_reads_normal_env_var() -> None:
    env = {"HARDWISE_MODEL_NORMAL": "mimo-v2.5"}
    assert ModelRouter(env).select("normal") == "mimo-v2.5"


def test_select_deep_reads_deep_env_var() -> None:
    env = {
        "HARDWISE_MODEL_NORMAL": "mimo-v2.5",
        "HARDWISE_MODEL_DEEP": "mimo-v2.5-pro",
    }
    assert ModelRouter(env).select("deep") == "mimo-v2.5-pro"


def test_missing_tier_falls_back_to_normal() -> None:
    env = {"HARDWISE_MODEL_NORMAL": "mimo-v2.5"}
    assert ModelRouter(env).select("fast") == "mimo-v2.5"
    assert ModelRouter(env).select("deep") == "mimo-v2.5"


def test_no_env_vars_uses_final_fallback() -> None:
    assert ModelRouter({}).select("normal") == "mimo-v2.5"


def test_empty_string_env_var_treated_as_missing() -> None:
    env = {"HARDWISE_MODEL_FAST": "  ", "HARDWISE_MODEL_NORMAL": "mimo-v2.5"}
    assert ModelRouter(env).select("fast") == "mimo-v2.5"


def test_default_tier_is_normal() -> None:
    env = {"HARDWISE_MODEL_NORMAL": "mimo-v2.5"}
    assert ModelRouter(env).select() == "mimo-v2.5"
