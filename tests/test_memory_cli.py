from typer.testing import CliRunner

from obsidian_agent.cli import app


runner = CliRunner()


def test_memory_cli_add_list_and_search(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"

    add_result = runner.invoke(app, ["memory", "add", "User prefers concise answers.", "--data-dir", str(data_dir)])
    list_result = runner.invoke(app, ["memory", "list", "--data-dir", str(data_dir)])
    search_result = runner.invoke(app, ["memory", "search", "concise answers", "--data-dir", str(data_dir)])

    assert add_result.exit_code == 0
    assert "Added memory: 1" in add_result.stdout
    assert list_result.exit_code == 0
    assert "User prefers concise answers." in list_result.stdout
    assert search_result.exit_code == 0
    assert "score=" in search_result.stdout
    assert "User prefers concise answers." in search_result.stdout


def test_memory_cli_delete_requires_confirmation(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"
    assert runner.invoke(app, ["memory", "add", "Delete me.", "--data-dir", str(data_dir)]).exit_code == 0

    cancel_result = runner.invoke(app, ["memory", "delete", "1", "--data-dir", str(data_dir)], input="n\n")
    list_after_cancel = runner.invoke(app, ["memory", "list", "--data-dir", str(data_dir)])
    delete_result = runner.invoke(app, ["memory", "delete", "1", "--data-dir", str(data_dir)], input="y\n")
    list_after_delete = runner.invoke(app, ["memory", "list", "--data-dir", str(data_dir)])

    assert cancel_result.exit_code == 1
    assert "Delete memory 1?" in cancel_result.stdout
    assert "Cancelled" in cancel_result.stdout
    assert "Delete me." in list_after_cancel.stdout
    assert delete_result.exit_code == 0
    assert "Deleted memory: 1" in delete_result.stdout
    assert "No memories" in list_after_delete.stdout


def test_memory_cli_delete_force_skips_confirmation(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"
    assert runner.invoke(app, ["memory", "add", "Delete me.", "--data-dir", str(data_dir)]).exit_code == 0

    result = runner.invoke(app, ["memory", "delete", "1", "--data-dir", str(data_dir), "--force"])

    assert result.exit_code == 0
    assert "Delete memory 1?" not in result.stdout
    assert "Deleted memory: 1" in result.stdout


def test_memory_cli_delete_missing_id_is_clear(tmp_path):
    data_dir = tmp_path / ".obsidian-agent"

    result = runner.invoke(app, ["memory", "delete", "404", "--data-dir", str(data_dir), "--force"])

    assert result.exit_code == 1
    assert "Memory not found: 404" in result.stdout
