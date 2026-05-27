from pathlib import Path
import shutil

from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_ask_uses_fake_providers_and_prints_sources(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(
        app,
        ["ask", "What does the project say?", "--data-dir", str(data_dir), "--embedding-provider", "fake", "--llm-provider", "fake"],
    )

    assert result.exit_code == 0
    assert "Fake answer" in result.stdout
    assert "Sources:" in result.stdout
    assert "Project.md" in result.stdout


def test_ask_show_context_prints_retrieved_chunks(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "ask",
            "What does the project say?",
            "--data-dir",
            str(data_dir),
            "--embedding-provider",
            "fake",
            "--llm-provider",
            "fake",
            "--show-context",
            "--context-chars",
            "40",
        ],
    )

    assert result.exit_code == 0
    assert "Contexts:" in result.stdout
    assert "Project.md" in result.stdout
    assert "score=" in result.stdout


def test_ask_top_k_limits_retrieved_contexts(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "ask",
            "What does the project say?",
            "--data-dir",
            str(data_dir),
            "--embedding-provider",
            "fake",
            "--llm-provider",
            "fake",
            "--show-context",
            "--top-k",
            "1",
        ],
    )

    assert result.exit_code == 0
    assert result.stdout.count("score=") == 1


def test_ask_can_include_local_memory(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0
    assert runner.invoke(app, ["memory", "add", "User prefers concise answers.", "--data-dir", str(data_dir)]).exit_code == 0

    result = runner.invoke(
        app,
        [
            "ask",
            "What concise answers preference should you remember?",
            "--data-dir",
            str(data_dir),
            "--embedding-provider",
            "fake",
            "--llm-provider",
            "fake",
            "--use-memory",
        ],
    )

    assert result.exit_code == 0
    assert "Sources:" in result.stdout
    assert "memory" in result.stdout
