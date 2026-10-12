"""Tests de la configuration (L2.2)."""

from config.settings import Settings


def test_import_has_no_side_effect_without_keys(monkeypatch):
    for var in ("TAVILY_API_KEY", "GROQ_API_KEY", "GROQ_API_KEYS", "LANGCHAIN_TRACING_V2"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=None)
    assert s.TAVILY_API_KEY is None
    assert s.GROQ_API_KEYS == []
    assert s.LANGCHAIN_TRACING_V2 is False
    assert s.DEVICE_PREFERENCE == "auto"
    assert not hasattr(s, "FORCE_GPU")


def test_groq_keys_are_merged_and_deduplicated(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("GROQ_API_KEYS", "k2, k1 ,k3,")
    assert Settings(_env_file=None).GROQ_API_KEYS == ["k1", "k2", "k3"]


def test_empty_values_become_none(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "")
    assert Settings(_env_file=None).TAVILY_API_KEY is None


def test_pipeline_setting_overridable_by_env(monkeypatch):
    monkeypatch.setenv("RERANKER_FINAL_K", "5")
    assert Settings(_env_file=None).RERANKER_FINAL_K == 5
