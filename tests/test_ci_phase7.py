from pathlib import Path

import yaml


def test_ci_has_required_release_gates():
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    quality_steps = "\n".join(
        str(step.get("run", "")) for step in jobs["quality"]["steps"]
    )
    assert "python -m pytest -q" in quality_steps
    assert "python -m evaluation.hallucination" in quality_steps
    assert "python -m alembic upgrade head" in quality_steps
    assert "python -m pip_audit" in quality_steps
    assert any(
        step.get("uses", "").startswith("gitleaks/gitleaks-action@")
        for step in jobs["secrets"]["steps"]
    )


def test_ci_permissions_are_read_only():
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    assert workflow["permissions"] == {"contents": "read"}


def test_deployment_runs_migrations_before_web_process():
    procfile = Path("Procfile").read_text(encoding="utf-8")
    assert "release: python -m alembic upgrade head" in procfile


def test_secret_scan_excludes_only_the_previously_tracked_vendor_environment():
    config = Path(".gitleaks.toml").read_text(encoding="utf-8")
    assert "useDefault = true" in config
    assert "^ai_tutor_env/" in config
    assert config.count("paths =") == 1
