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
