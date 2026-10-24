"""The tools Jarvis ships with.

Nothing here can write, delete, or execute. A shell tool is the obvious next
addition and deliberately absent: it hands the model arbitrary code execution on
the host, which is a decision to make on purpose rather than inherit from a
scaffold. Add it behind a confirmation prompt when you need it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from jarvis.config import Settings
from jarvis.tools.registry import ToolRegistry

MAX_READ_BYTES = 100_000


class WorkspaceError(ValueError):
    """Raised when a path escapes the configured workspace."""


def resolve_in_workspace(workspace: Path, candidate: str) -> Path:
    """Resolve ``candidate`` against ``workspace``, refusing anything outside it.

    Symlinks are resolved before the check, so a link pointing out of the
    workspace is rejected too.
    """
    root = workspace.resolve()
    raw = Path(candidate)
    target = raw.resolve() if raw.is_absolute() else (root / raw).resolve()
    if target != root and root not in target.parents:
        raise WorkspaceError(f"{candidate!r} is outside the workspace ({root})")
    return target


def read_text_file(workspace: Path, path: str) -> str:
    """Read a UTF-8 text file from inside ``workspace``, truncating long files."""
    target = resolve_in_workspace(workspace, path)
    if not target.is_file():
        raise FileNotFoundError(f"no such file: {path}")
    data = target.read_bytes()[: MAX_READ_BYTES + 1]
    text = data.decode("utf-8", errors="replace")
    if len(data) > MAX_READ_BYTES:
        return text[:MAX_READ_BYTES] + f"\n\n[truncated at {MAX_READ_BYTES} bytes]"
    return text


def list_workspace_dir(workspace: Path, path: str = ".") -> str:
    """List the entries of a directory inside ``workspace``."""
    target = resolve_in_workspace(workspace, path)
    if not target.is_dir():
        raise NotADirectoryError(f"not a directory: {path}")
    entries = sorted(
        f"{child.name}/" if child.is_dir() else child.name for child in target.iterdir()
    )
    return "\n".join(entries) if entries else "(empty)"


def build_registry(settings: Settings) -> ToolRegistry:
    """Build the default registry, closing over ``settings`` for workspace access."""
    registry = ToolRegistry()
    workspace = settings.workspace

    @registry.register
    def current_time() -> str:
        """Get the current date and time in UTC, as an ISO 8601 string."""
        return datetime.now(UTC).isoformat(timespec="seconds")

    @registry.register
    def read_file(path: str) -> str:
        """Read a text file from the workspace.

        Args:
            path: Path to the file, relative to the workspace root.
        """
        try:
            return read_text_file(workspace, path)
        except (WorkspaceError, OSError) as exc:
            return f"error: {exc}"

    @registry.register
    def list_directory(path: str = ".") -> str:
        """List the files and subdirectories of a workspace directory.

        Args:
            path: Directory path relative to the workspace root. Defaults to the root.
        """
        try:
            return list_workspace_dir(workspace, path)
        except (WorkspaceError, OSError) as exc:
            return f"error: {exc}"

    return registry
