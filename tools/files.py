"""ATLAS file tools, limited to folders the user allowlisted in Settings."""
import shutil
from pathlib import Path
from security.policy import Risk
from .registry import tool

_settings = None
TRASH = None


def configure(settings, trash_dir):
    global _settings, TRASH
    _settings, TRASH = settings, Path(trash_dir)


def _safe(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    roots = [Path(r).expanduser().resolve() for r in (_settings.get("allowed_folders") if _settings else [])]
    if not any(p == r or r in p.parents for r in roots):
        raise PermissionError(f"{p} is outside your allowed folders (Settings > Allowed folders).")
    return p


@tool("list_folder", "List files in an allowed folder", {"path": str}, Risk.READ)
def list_folder(path):
    p = _safe(path)
    return [f"{'[D]' if c.is_dir() else '   '} {c.name}" for c in sorted(p.iterdir())][:300]


@tool("read_file", "Read a text file in an allowed folder", {"path": str}, Risk.READ)
def read_file(path):
    return _safe(path).read_text(encoding="utf-8", errors="ignore")[:20000]


@tool("create_file", "Create a NEW text file (never overwrites)", {"path": str, "content": str}, Risk.WRITE,
      preview=lambda a: f"Create {a['path']} with {len(a['content'])} characters:\n\n{a['content'][:800]}")
def create_file(path, content):
    p = _safe(path)
    if p.exists():
        raise FileExistsError(f"{p} already exists; JARVIS never overwrites.")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"Created {p}"


@tool("move_file", "Move or rename a file inside allowed folders", {"src": str, "dst": str}, Risk.DESTRUCTIVE,
      preview=lambda a: f"Move\n  {a['src']}\n→ {a['dst']}")
def move_file(src, dst):
    s, d = _safe(src), _safe(dst)
    if d.exists():
        raise FileExistsError(f"{d} already exists.")
    shutil.move(str(s), str(d))
    return f"Moved to {d}"


@tool("delete_file", "Delete a file (moved to JARVIS trash, restorable)", {"path": str}, Risk.DESTRUCTIVE,
      preview=lambda a: f"DELETE {a['path']}\n(It goes to the JARVIS trash folder so you can restore it.)")
def delete_file(path):
    p = _safe(path)
    TRASH.mkdir(parents=True, exist_ok=True)
    target = TRASH / p.name
    i = 1
    while target.exists():
        target = TRASH / f"{p.stem}_{i}{p.suffix}"
        i += 1
    shutil.move(str(p), str(target))
    return f"Moved to trash: {target}"
