import pytest

from jarvis.tools.builtin import (
    WorkspaceError,
    list_workspace_dir,
    read_text_file,
    resolve_in_workspace,
)


def test_reads_a_file_inside_the_workspace(tmp_path):
    (tmp_path / "note.txt").write_text("hello", encoding="utf-8")
    assert read_text_file(tmp_path, "note.txt") == "hello"


def test_rejects_a_path_that_escapes_the_workspace(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")

    with pytest.raises(WorkspaceError):
        read_text_file(workspace, "../secret.txt")


def test_rejects_an_absolute_path_outside_the_workspace(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()

    with pytest.raises(WorkspaceError):
        resolve_in_workspace(workspace, "/etc/passwd")


def test_rejects_a_symlink_pointing_out_of_the_workspace(tmp_path):
    workspace = tmp_path / "ws"
    workspace.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("nope", encoding="utf-8")
    (workspace / "link.txt").symlink_to(outside)

    with pytest.raises(WorkspaceError):
        read_text_file(workspace, "link.txt")


def test_truncates_a_long_file(tmp_path, monkeypatch):
    monkeypatch.setattr("jarvis.tools.builtin.MAX_READ_BYTES", 10)
    (tmp_path / "big.txt").write_text("x" * 50, encoding="utf-8")

    result = read_text_file(tmp_path, "big.txt")
    assert result.startswith("x" * 10)
    assert "truncated" in result


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_text_file(tmp_path, "absent.txt")


def test_lists_a_directory(tmp_path):
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    (tmp_path / "sub").mkdir()

    assert list_workspace_dir(tmp_path, ".") == "a.txt\nsub/"


def test_lists_an_empty_directory(tmp_path):
    assert list_workspace_dir(tmp_path, ".") == "(empty)"
