"""Typed, allowlisted tools. The model may only call what is registered here."""
import json
from dataclasses import dataclass
from typing import Callable
from security.policy import Risk, EmergencyStop
from storage.db import audit, db


@dataclass
class Tool:
    name: str
    description: str
    params: dict           # {"path": str}
    risk: Risk
    func: Callable
    preview: Callable = None  # args -> human-readable preview

    def validate(self, args: dict):
        for k, t in self.params.items():
            if k not in args:
                raise ValueError(f"Missing argument '{k}' for {self.name}")
            if not isinstance(args[k], t):
                raise ValueError(f"Argument '{k}' must be {t.__name__}")
        extra = set(args) - set(self.params)
        if extra:
            raise ValueError(f"Unknown arguments: {extra}")


class Registry:
    def __init__(self):
        self.tools = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def describe(self, allowed):
        lines = []
        for n in allowed:
            t = self.tools.get(n)
            if t:
                sig = ", ".join(f"{k}: {v.__name__}" for k, v in t.params.items())
                lines.append(f"- {t.name}({sig}): {t.description}")
        return "\n".join(lines)

    def run(self, name, args, gate, allowed):
        if EmergencyStop.active():
            return {"ok": False, "error": "Emergency stop is active."}
        if name not in allowed or name not in self.tools:
            audit("tool_blocked", f"{name} not allowed")
            return {"ok": False, "error": f"Tool '{name}' is not permitted for this companion."}
        tool = self.tools[name]
        try:
            tool.validate(args)
            preview = tool.preview(args) if tool.preview else f"{name}({json.dumps(args)})"
        except Exception as e:
            return {"ok": False, "error": str(e)}
        if not gate.check(name, args, tool.risk, preview):
            audit("tool_denied", f"{name} {json.dumps(args)}")
            return {"ok": False, "error": "User denied this action."}
        try:
            result = tool.func(**args)
            audit("tool_ok", f"{name} {json.dumps(args)[:500]}")
            return {"ok": True, "result": result}
        except Exception as e:
            audit("tool_error", f"{name}: {e}")
            return {"ok": False, "error": str(e)}


REGISTRY = Registry()


def tool(name, description, params, risk, preview=None):
    def deco(fn):
        REGISTRY.register(Tool(name, description, params, risk, fn, preview))
        return fn
    return deco


def list_tasks_impl():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT id, title, status FROM tasks ORDER BY id DESC LIMIT 20")]
