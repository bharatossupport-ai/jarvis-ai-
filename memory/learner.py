"""Learns while chatting: pulls durable facts/preferences out of each exchange.

- Explicit: "remember that…", "yaad rakhna…", "याद रखो…" → saved immediately.
- Implicit: after each reply a short background model call extracts lasting facts
  (name, likes, projects, routines). Small talk and one-off requests are ignored.
Every learned item appears in the Memory page, where it can be edited or deleted.
"""
import json
import re
from difflib import SequenceMatcher
from . import store

EXPLICIT = re.compile(
    r"^\s*(?:please\s+)?(?:remember(?:\s+that)?|note(?:\s+that)?|yaad\s+rakh(?:o|na|iye)?|याद\s+रख(?:ो|ना|िए|ें)?)\s*[:,-]?\s*(.+)",
    re.I | re.S)
FORGET = re.compile(r"^\s*(?:forget|bhool\s+jao|भूल\s+जाओ)\s+(?:that\s+)?(.+)", re.I | re.S)

EXTRACT_PROMPT = """Extract LONG-TERM facts about the user from this exchange: their name, preferences,
likes/dislikes, goals, projects, people in their life, routines, skills, language preference.
Ignore one-off requests, questions, and anything about the assistant. Write each fact as one short
sentence in English, starting with "User". If nothing is worth remembering, return [].
Reply with ONLY a JSON list of objects: [{"fact": "...", "category": "preference|project|knowledge|episodic"}]

User said: {user}
Assistant replied: {assistant}"""


def _similar(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio() > 0.82


def _is_new(fact):
    return not any(_similar(fact, m["content"]) for m in store.list_memories())


def explicit(text, scope="shared"):
    """Returns ('saved'|'forgot'|None, content)."""
    m = EXPLICIT.match(text)
    if m:
        fact = m.group(1).strip().rstrip(".")
        if _is_new(fact):
            store.add_memory(fact, "preference", scope)
        return "saved", fact
    f = FORGET.match(text)
    if f:
        target = f.group(1).strip()
        hits = [mm for mm in store.list_memories() if target.lower() in mm["content"].lower()
                or _similar(target, mm["content"])]
        for h in hits:
            store.delete_memory(h["id"])
        return "forgot", f"{len(hits)} item(s)"
    return None, None


def extract(router, user_text, assistant_text, auto_approve=True, scope="shared"):
    """Background call. Returns the list of facts it saved."""
    if len(user_text.split()) < 3:
        return []
    prompt = EXTRACT_PROMPT.replace("{user}", user_text[:1500]).replace("{assistant}", assistant_text[:1000])
    try:
        raw, _ = router.chat([{"role": "user", "content": prompt}])
        raw = raw[raw.find("["): raw.rfind("]") + 1]
        items = json.loads(raw) if raw else []
    except Exception:
        return []
    saved = []
    for it in items[:5]:
        fact = (it.get("fact") or "").strip() if isinstance(it, dict) else ""
        cat = it.get("category", "preference") if isinstance(it, dict) else "preference"
        if 8 < len(fact) < 300 and _is_new(fact):
            if cat not in store.CATEGORIES:
                cat = "preference"
            (store.add_memory if auto_approve else store.propose_memory)(fact, cat, scope)
            saved.append(fact)
    return saved
