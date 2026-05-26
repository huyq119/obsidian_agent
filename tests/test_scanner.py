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


def test_scanner_records_warning_and_continues_after_parse_error(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Valid.md").write_text("# Valid\n\nStill scanned.\n", encoding="utf-8")
    (vault / "Broken.md").write_text("---\ntags: [broken\n---\n# Broken\n", encoding="utf-8")

    result = scan_vault_files(vault, ScanConfig())

    assert [note.path for note in result.notes] == ["Valid.md"]
    assert len(result.warnings) == 1
    assert "Broken.md" in result.warnings[0]
    assert result.scanned_files == 1
