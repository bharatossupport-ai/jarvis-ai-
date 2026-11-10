"""Policy engine: runs outside the model. Every tool call passes through here."""
import json
import threading
from enum import Enum
from storage.db import db, audit


class Risk(str, Enum):
    LOW = "low"                # answer / summarise
    READ = "read"              # read user-selected file or folder
    WRITE = "write"            # reversible create
    DESTRUCTIVE = "destructive"  # delete, overwrite, bulk move
    EXTERNAL = "external"      # send, submit, install, settings, launch apps, browser actions


NEEDS_APPROVAL = {Risk.WRITE, Risk.DESTRUCTIVE, Risk.EXTERNAL}


class EmergencyStop:
    _event = threading.Event()

    @classmethod
    def trigger(cls):
        cls._event.set()
        audit("emergency_stop", "All tasks halted by user")

    @classmethod
    def reset(cls):
        cls._event.clear()

    @classmethod
    def active(cls):
        return cls._event.is_set()


class ApprovalGate:
    """Blocks a worker thread until the UI answers. Approval is tied to the exact tool+args."""

    def __init__(self, ask_ui):
        self.ask_ui = ask_ui  # callable(tool, args, risk, preview) -> bool (thread-safe, blocking)

    def check(self, tool_name, args, risk: Risk, preview: str) -> bool:
        if EmergencyStop.active():
            return False
        if risk not in NEEDS_APPROVAL:
            decision = True
        else:
            decision = bool(self.ask_ui(tool_name, args, risk, preview))
        with db() as c:
            c.execute("INSERT INTO approvals(tool, args, risk, decision) VALUES(?,?,?,?)",
                      (tool_name, json.dumps(args), risk.value, "approved" if decision else "denied"))
        return decision


def recent_audit(limit=200):
    with db() as c:
        return [dict(r) for r in c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,))]
