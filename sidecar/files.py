"""Scoped local file access for work outside the cloud checkout.

All paths are resolved and confined to a single root directory (default: the
user's home). Anything that resolves outside the root — including via ``..`` or
a symlink — is refused, so Claude can read and write your files for local tasks
without being able to wander the whole disk.
"""

from __future__ import annotations

from pathlib import Path


class FileAccessError(RuntimeError):
    pass


# Read caps, so a stray "read this" on a huge/binary file can't blow up context.
MAX_READ_BYTES = 1_000_000


class FileScope:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise FileAccessError(f"file root is not a directory: {self.root}")

    def _resolve(self, path: str) -> Path:
        # Resolve against the root, following symlinks, then confirm containment.
        candidate = (self.root / path).expanduser()
        try:
            resolved = candidate.resolve()
        except OSError as e:
            raise FileAccessError(f"cannot resolve {path!r}: {e}") from e
        if resolved != self.root and self.root not in resolved.parents:
            raise FileAccessError(
                f"{path!r} is outside the allowed root ({self.root}); refused"
            )
        return resolved

    def list_dir(self, path: str = ".") -> str:
        target = self._resolve(path)
        if not target.is_dir():
            raise FileAccessError(f"not a directory: {path}")
        lines = []
        for child in sorted(target.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
            if child.is_dir():
                lines.append(f"{child.name}/")
            else:
                try:
                    size = child.stat().st_size
                    lines.append(f"{child.name}  ({size} bytes)")
                except OSError:
                    lines.append(child.name)
        rel = target.relative_to(self.root) if target != self.root else Path(".")
        header = f"{rel} ({len(lines)} entries):"
        return "\n".join([header, *lines]) if lines else f"{rel} is empty."

    def read_file(self, path: str) -> str:
        target = self._resolve(path)
        if not target.is_file():
            raise FileAccessError(f"not a file: {path}")
        size = target.stat().st_size
        if size > MAX_READ_BYTES:
            raise FileAccessError(
                f"{path} is {size} bytes, over the {MAX_READ_BYTES}-byte read limit"
            )
        try:
            return target.read_text(encoding="utf-8")
        except UnicodeDecodeError as e:
            raise FileAccessError(f"{path} is not UTF-8 text; cannot read as text") from e

    def write_file(self, path: str, content: str, append: bool = False) -> str:
        target = self._resolve(path)
        if target.is_dir():
            raise FileAccessError(f"{path} is a directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as f:
            f.write(content)
        verb = "appended to" if append else "wrote"
        return f"{verb} {target.relative_to(self.root)} ({len(content)} chars)"
