from pathlib import Path

from app.policy import POLICY_MARKER, REFUSAL_MESSAGE, TOPIC_REFUSAL

ROOT = Path(__file__).resolve().parents[1]


def test_policy_marker_is_in_the_guardrails_config() -> None:
    config = (ROOT / "guardrails" / "config.yml").read_text(encoding="utf-8")
    assert POLICY_MARKER in config
    assert "self check input" in config
    assert "self check output" in config
    assert "jailbreak pattern check" in config
    assert "mask pii on input" in config
    assert "mask pii on output" in config


def test_prompts_use_the_documented_variables() -> None:
    prompts = (ROOT / "guardrails" / "prompts.yml").read_text(encoding="utf-8")
    assert "self_check_input" in prompts
    assert "self_check_output" in prompts
    assert "{{ user_input }}" in prompts
    assert "{{ bot_response }}" in prompts


def test_refusal_strings_match_the_colang_files() -> None:
    checks = (ROOT / "guardrails" / "rails" / "checks.co").read_text(encoding="utf-8")
    topics = (ROOT / "guardrails" / "rails" / "topics.co").read_text(encoding="utf-8")
    assert REFUSAL_MESSAGE in checks
    assert TOPIC_REFUSAL in topics


def test_env_example_has_no_real_key() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "LLM_API_KEY=" in example
    assert "sk-" not in example
    assert "ENABLE_JAILBREAK_HEURISTICS=0" in example


def test_sample_result_is_labeled_as_a_sample() -> None:
    sample = (ROOT / "results" / "sample" / "comparison.sample.json").read_text(encoding="utf-8")
    assert '"kind": "sample"' in sample
    assert "not a real scan" in sample.lower() or "not a Garak report" in sample
    page = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
    assert "SAMPLE" in page
    assert "not a real scan" in page.lower()


def test_dry_run_writes_configs(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(ROOT)
    from scripts.run_garak import main

    code = main(["--mode", "before", "--dry-run", "--base-url", "http://127.0.0.1:8000"])
    assert code == 0
    generated = ROOT / "results" / ".generated" / "rest.before.json"
    assert generated.is_file()
    assert "v1/chat/raw" in generated.read_text(encoding="utf-8")
    del tmp_path
