"""Request -> plan -> companion -> policy -> approval -> execute -> verify -> audit -> report."""
import json
import re
import threading
from datetime import datetime
from companions.profiles import COMPANIONS, route
from intelligence.providers import ModelRouter, ProviderError
from memory import store, learner
from security.policy import ApprovalGate, EmergencyStop
from storage.db import db, audit
from tools.registry import REGISTRY

TOOL_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.S)
MAX_STEPS = 4

LANGUAGE_RULES = {
    "auto": "The user may write in English, Hindi (Devanagari) or Hinglish (Hindi in Roman letters). "
            "Always reply in the same language and script the user used in their latest message.",
    "hi": "Always reply in Hindi using Devanagari script, even if the user writes in English or Hinglish.",
    "en": "Always reply in English, even if the user writes in Hindi or Hinglish.",
}

TOOL_PROTOCOL = """
You can use tools. To call one, reply with ONLY this block and nothing else:
```tool
{"tool": "<name>", "args": {...}}
```
You will then receive the tool result and can continue. Never claim an action succeeded
unless a tool result says ok. If no tool is needed, just answer normally.
Available tools:
"""


class Orchestrator:
    def __init__(self, settings, ask_approval):
        self.settings = settings
        self.router = ModelRouter(settings)
        self.gate = ApprovalGate(ask_approval)
        self.extra_tools = []  # tools added by enabled connectors

    def _system_prompt(self, comp):
        mems = store.memories_for(comp.scope)
        allowed = comp.tools + self.extra_tools
        parts = [comp.instructions,
                 f"Today is {datetime.now():%A %d %B %Y, %H:%M}.",
                 LANGUAGE_RULES[self.settings.get("language")]]
        if mems:
            parts.append("Things the user has approved for you to remember:\n- " + "\n- ".join(mems))
        if allowed:
            parts.append(TOOL_PROTOCOL + REGISTRY.describe(allowed))
        return "\n\n".join(parts), allowed

    def _task(self, title, companion):
        with db() as c:
            return c.execute("INSERT INTO tasks(title, status, companion, updated) VALUES(?, 'running', ?, ?)",
                             (title[:120], companion, datetime.now().isoformat())).lastrowid

    def _finish(self, tid, status, result):
        with db() as c:
            c.execute("UPDATE tasks SET status=?, result=?, updated=? WHERE id=?",
                      (status, result[:2000], datetime.now().isoformat(), tid))

    def handle(self, conv_id, text, current_companion="JARVIS", on_token=None, on_event=None):
        """Runs in a worker thread. Returns (reply, companion_name, model_label)."""
        EmergencyStop.reset()
        comp = route(text, current_companion)
        clean = re.sub(r"^@\w+\s*", "", text)
        store.add_message(conv_id, "user", clean, comp.name)
        tid = self._task(clean, comp.name)
        if on_event:
            on_event("companion", comp.name)
        kind, fact = learner.explicit(clean)
        if kind and on_event:
            on_event("learned" if kind == "saved" else "forgot", fact)

        system, allowed = self._system_prompt(comp)
        history = store.messages(conv_id, self.settings.get("max_context_messages"))
        msgs = [{"role": "system", "content": system}] + [
            {"role": m["role"], "content": m["content"]} for m in history if m["role"] in ("user", "assistant")]

        model_label, reply = "", ""
        try:
            for _ in range(MAX_STEPS):
                if EmergencyStop.active():
                    reply = "Stopped by emergency stop."
                    break
                buffer = []
                reply, model_label = self.router.chat(msgs, stream_cb=lambda t: buffer.append(t))
                m = TOOL_RE.search(reply)
                if not m:
                    if on_token:
                        on_token(reply)
                    break
                try:
                    call = json.loads(m.group(1))
                    name, args = call["tool"], call.get("args", {})
                except (json.JSONDecodeError, KeyError) as e:
                    result = {"ok": False, "error": f"Bad tool call: {e}"}
                    name = "?"
                else:
                    if on_event:
                        on_event("tool", name)
                    result = REGISTRY.run(name, args, self.gate, allowed)
                msgs.append({"role": "assistant", "content": reply})
                msgs.append({"role": "user", "content": f"Tool result for {name}: {json.dumps(result, default=str)[:6000]}"})
            else:
                reply = reply if not TOOL_RE.search(reply) else "I stopped after several tool steps. Here is where I got to."
                if on_token:
                    on_token(reply)
            self._finish(tid, "done", reply)
        except ProviderError as e:
            reply = f"⚠ {e}"
            self._finish(tid, "failed", reply)
            audit("model_error", str(e))
        store.add_message(conv_id, "assistant", reply, comp.name, model_label)
        if self.settings.get("auto_learn") and not kind and not reply.startswith("⚠"):
            threading.Thread(target=self._learn, args=(clean, reply, on_event), daemon=True).start()
        return reply, comp.name, model_label

    def _learn(self, user_text, reply, on_event):
        for fact in learner.extract(self.router, user_text, reply, self.settings.get("auto_approve_learned")):
            audit("learned", fact)
            if on_event:
                on_event("learned", fact)

    def run_headless(self, prompt, companion="JARVIS"):
        """Used by workflows. Consequential actions still need approval in the UI."""
        conv = store.new_conversation(f"Workflow: {prompt[:30]}", companion)
        reply, _, _ = self.handle(conv, f"@{companion} {prompt}")
        return reply
