from typer.testing import CliRunner

from obsidian_agent import __version__


def test_package_version_is_defined():
    assert __version__ == "0.1.0"
