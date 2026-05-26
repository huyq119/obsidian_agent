from pathlib import Path
import shutil

from obsidian_agent.config import ScanConfig
from obsidian_agent.vault.scanner import scan_vault_files


def test_scanner_reads_markdown_and_skips_obsidian(tmp_path):
    source = Path("tests/fixtures/vault_basic")
    vault = tmp_path / "vault"
    shutil.copytree(source, vault)

    result = scan_vault_files(vault, ScanConfig())

    assert result.warnings == []
    assert sorted(note.path for note in result.notes) == ["Inbox/Loose.md", "Project.md"]
    assert all(".obsidian" not in note.path for note in result.notes)
    assert result.scanned_files == 2
