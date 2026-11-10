"""Conversations, user-approved memory, projects, documents and search."""
import json
from pathlib import Path
from storage.db import db

CATEGORIES = ["preference", "project", "episodic", "knowledge", "companion"]


# ---- conversations -------------------------------------------------------
def new_conversation(title="New chat", companion="JARVIS", project_id=None):
    with db() as c:
        cur = c.execute("INSERT INTO conversations(title, companion, project_id) VALUES(?,?,?)",
                        (title, companion, project_id))
        return cur.lastrowid


def list_conversations():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM conversations ORDER BY id DESC")]


def add_message(conv_id, role, content, companion=None, model=None):
    with db() as c:
        c.execute("INSERT INTO messages(conversation_id, role, companion, model, content) VALUES(?,?,?,?,?)",
                  (conv_id, role, companion, model, content))
        c.execute("INSERT INTO search_index(kind, ref, text) VALUES('message', ?, ?)", (str(conv_id), content))
        if role == "user":
            row = c.execute("SELECT title FROM conversations WHERE id=?", (conv_id,)).fetchone()
            if row and row["title"] == "New chat":
                c.execute("UPDATE conversations SET title=? WHERE id=?", (content[:40], conv_id))


def messages(conv_id, limit=None):
    q = "SELECT * FROM messages WHERE conversation_id=? ORDER BY id"
    with db() as c:
        rows = [dict(r) for r in c.execute(q, (conv_id,))]
    return rows[-limit:] if limit else rows


def delete_conversation(conv_id):
    with db() as c:
        c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))
        c.execute("DELETE FROM search_index WHERE kind='message' AND ref=?", (str(conv_id),))


def export_conversation(conv_id, path):
    Path(path).write_text(json.dumps(messages(conv_id), indent=2, ensure_ascii=False), encoding="utf-8")


# ---- long-term memory (user approved) ------------------------------------
def propose_memory(content, category="preference", scope="shared"):
    """Saved unapproved; it is used only once the user approves it in the Memory page."""
    with db() as c:
        return c.execute("INSERT INTO memories(category, scope, content, approved) VALUES(?,?,?,0)",
                         (category, scope, content)).lastrowid


def add_memory(content, category="preference", scope="shared"):
    with db() as c:
        mid = c.execute("INSERT INTO memories(category, scope, content, approved) VALUES(?,?,?,1)",
                        (category, scope, content)).lastrowid
        c.execute("INSERT INTO search_index(kind, ref, text) VALUES('memory', ?, ?)", (str(mid), content))
        return mid


def approve_memory(mid):
    with db() as c:
        c.execute("UPDATE memories SET approved=1 WHERE id=?", (mid,))
        row = c.execute("SELECT content FROM memories WHERE id=?", (mid,)).fetchone()
        c.execute("INSERT INTO search_index(kind, ref, text) VALUES('memory', ?, ?)", (str(mid), row["content"]))


def update_memory(mid, content):
    with db() as c:
        c.execute("UPDATE memories SET content=? WHERE id=?", (content, mid))
        c.execute("UPDATE search_index SET text=? WHERE kind='memory' AND ref=?", (content, str(mid)))


def delete_memory(mid):
    with db() as c:
        c.execute("DELETE FROM memories WHERE id=?", (mid,))
        c.execute("DELETE FROM search_index WHERE kind='memory' AND ref=?", (str(mid),))


def list_memories(approved=None):
    q, args = "SELECT * FROM memories", ()
    if approved is not None:
        q, args = q + " WHERE approved=?", (1 if approved else 0,)
    with db() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id DESC", args)]


def memories_for(companion_scope):
    """Approved memories visible to a companion: shared ones plus its own scope."""
    with db() as c:
        return [r["content"] for r in c.execute(
            "SELECT content FROM memories WHERE approved=1 AND scope IN ('shared', ?) ORDER BY id DESC LIMIT 30",
            (companion_scope,))]


# ---- projects & documents -------------------------------------------------
def add_project(name, notes=""):
    with db() as c:
        return c.execute("INSERT OR IGNORE INTO projects(name, notes) VALUES(?,?)", (name, notes)).lastrowid


def list_projects():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM projects ORDER BY name")]


def add_document(path):
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")[:200_000]
    with db() as c:
        did = c.execute("INSERT INTO documents(path, title, content) VALUES(?,?,?)",
                        (str(p), p.name, text)).lastrowid
        c.execute("INSERT INTO search_index(kind, ref, text) VALUES('document', ?, ?)", (str(did), text))
        return did


# ---- search ----------------------------------------------------------------
def search(query, limit=10):
    with db() as c:
        try:
            rows = c.execute("SELECT kind, ref, snippet(search_index, 2, '[', ']', '…', 12) AS s "
                             "FROM search_index WHERE search_index MATCH ? LIMIT ?", (query, limit)).fetchall()
        except Exception:
            rows = c.execute("SELECT kind, ref, substr(text, 1, 160) AS s FROM search_index "
                             "WHERE text LIKE ? LIMIT ?", (f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]
