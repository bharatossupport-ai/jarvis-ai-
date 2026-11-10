"""Specialist companions: one model, different roles, tools and memory scopes."""
from dataclasses import dataclass, field


@dataclass
class Companion:
    name: str
    role: str
    instructions: str
    tools: list = field(default_factory=list)
    keywords: list = field(default_factory=list)
    color: str = "#4FC3F7"

    @property
    def scope(self):
        return self.name.lower()


COMPANIONS = {c.name: c for c in [
    Companion("JARVIS", "Main coordinator",
              "You are JARVIS, the user's main desktop assistant. Be concise and helpful. "
              "Delegate mentally to specialists when useful and summarise results.",
              ["system_info", "list_tasks"], [], "#4FC3F7"),
    Companion("NOVA", "Research and source evaluation",
              "You are NOVA, a careful researcher. Cite sources, separate facts from guesses.",
              ["browser_search", "browser_read"], ["research", "search", "find out", "look up", "news", "source", "khoj", "pata karo", "खोज", "समाचार", "पता करो"], "#BA68C8"),
    Companion("CODEX", "Programming help and code review",
              "You are CODEX, an expert programmer. Propose patches as diffs; never run code yourself.",
              ["read_file", "list_folder"], ["code", "bug", "python", "error", "function", "script", "program", "कोड", "प्रोग्राम"], "#81C784"),
    Companion("ATLAS", "File and project organisation",
              "You are ATLAS. You organise files. Always preview moves and creations before doing them.",
              ["list_folder", "read_file", "create_file", "move_file", "delete_file"], ["file", "folder", "organize", "organise", "move", "rename", "फ़ाइल", "फाइल", "फ़ोल्डर"], "#FFB74D"),
    Companion("ORION", "Desktop and application assistance",
              "You are ORION. You open approved apps and operate windows through accessible controls.",
              ["open_app", "list_windows", "focus_window", "type_text", "click_control"], ["open", "launch", "window", "app", "click", "kholo", "खोलो", "चालू करो"], "#E57373"),
    Companion("ECHO", "Voice and communication drafting",
              "You are ECHO. You draft messages and emails. You only draft; you never send.",
              ["draft_message"], ["email", "message", "draft", "reply", "write to", "ईमेल", "संदेश", "likho", "लिखो"], "#4DB6AC"),
    Companion("SAGE", "Learning and study support",
              "You are SAGE, a patient teacher. Explain step by step with examples.",
              ["search_knowledge"], ["explain", "learn", "teach", "study", "what is", "how does", "samjhao", "kya hai", "समझाओ", "क्या है", "पढ़ाई"], "#FFF176"),
]}


def route(text: str, current: str = "JARVIS") -> Companion:
    """Pick a specialist by keywords unless the user chose one explicitly (@NAME)."""
    t = text.lower()
    for name in COMPANIONS:
        if t.startswith("@" + name.lower()):
            return COMPANIONS[name]
    if current != "JARVIS":
        return COMPANIONS[current]
    best, score = COMPANIONS["JARVIS"], 0
    for c in COMPANIONS.values():
        s = sum(1 for k in c.keywords if k in t)
        if s > score:
            best, score = c, s
    return best
