from obsidian_agent.suggestions.reporter import render_markdown_report
from obsidian_agent.suggestions.rules import build_suggestions


def test_suggestions_find_missing_tags_frontmatter_and_isolated_notes():
    notes = [
        {
            "path": "Loose.md",
            "title": "Loose",
            "frontmatter_json": "{}",
            "tags_json": "[]",
            "links_json": "[]",
            "backlinks_count": 0,
            "outgoing_links_count": 0,
            "has_explicit_title": 1,
            "word_count": 1,
        }
    ]

    suggestions = build_suggestions(notes)
    kinds = {item.kind for item in suggestions}

    assert "missing_frontmatter" in kinds
    assert "missing_tags" in kinds
    assert "isolated_note" in kinds


def test_markdown_report_contains_note_paths():
    markdown = render_markdown_report([
        {"kind": "missing_tags", "path": "Loose.md", "message": "Add tags"}
    ])

    assert "# Obsidian Agent Suggestions" in markdown
    assert "Loose.md" in markdown


def test_suggest_refuses_output_inside_vault(tmp_path):
    from pathlib import Path
    import shutil
    from typer.testing import CliRunner
    from obsidian_agent.cli import app

    runner = CliRunner()
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)
    data_dir = tmp_path / ".obsidian-agent"

    assert runner.invoke(app, ["init", "--vault", str(vault), "--data-dir", str(data_dir)]).exit_code == 0
    assert runner.invoke(app, ["scan", "--data-dir", str(data_dir), "--embedding-provider", "fake"]).exit_code == 0

    result = runner.invoke(app, ["suggest", "--data-dir", str(data_dir), "--output", str(vault / "suggestions.md")])

    assert result.exit_code == 1
    assert "Refusing to write inside the vault" in result.stdout
    assert not (vault / "suggestions.md").exists()
