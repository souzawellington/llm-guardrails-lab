import json

from app.garak_config import DEFAULT_PROBES, parse_spec, write_configs


def test_default_spec_covers_the_four_lab_categories() -> None:
    joined = " ".join(DEFAULT_PROBES)
    assert "promptinject" in joined
    assert "dan.Dan_11_0" in joined
    assert "leakreplay" in joined
    assert "realtoxicityprompts" in joined


def test_parse_spec_uses_the_environment_override() -> None:
    assert parse_spec(None) == list(DEFAULT_PROBES)
    assert parse_spec(" probes.encoding ") == ["probes.encoding"]


def test_written_configs_have_no_secrets_and_point_at_the_right_route(tmp_path) -> None:
    report_dir = tmp_path / "results" / "before"
    config_path, generator_path = write_configs(
        tmp_path / "generated",
        base_url="http://127.0.0.1:8000",
        mode="before",
        probes=["probes.promptinject.HijackLongPrompt"],
        report_dir=report_dir,
    )
    generator = json.loads(generator_path.read_text(encoding="utf-8"))
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rest = generator["rest"]["RestGenerator"]
    assert rest["uri"] == "http://127.0.0.1:8000/v1/chat/raw"
    assert rest["response_json_field"] == "reply"
    assert "api_key" not in json.dumps(generator).lower()
    assert config["plugins"]["target_type"] == "rest"
    assert config["reporting"]["report_dir"] == str(report_dir)
    assert config["run"]["spec"]["include"] == ["probes.promptinject.HijackLongPrompt"]

    _, after_generator = write_configs(
        tmp_path / "generated",
        base_url="http://127.0.0.1:8000/",
        mode="after",
        probes=["probes.dan.Dan_11_0"],
        report_dir=tmp_path / "results" / "after",
    )
    after = json.loads(after_generator.read_text(encoding="utf-8"))
    assert after["rest"]["RestGenerator"]["uri"].endswith("/v1/chat/guarded")
