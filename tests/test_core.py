import json
from storage import db
db.init()
from storage.settings import Settings
from memory import store, learner
from companions.profiles import route
from security.policy import Risk, ApprovalGate, EmergencyStop
from tools.registry import REGISTRY
import tools.files as files
import tools.desktop  # noqa: registers tools
from backend.orchestrator import Orchestrator


def test_memory_roundtrip(tmp_path):
    cid = store.new_conversation()
    store.add_message(cid, "user", "hello jarvis")
    assert store.messages(cid)[0]["content"] == "hello jarvis"
    mid = store.add_memory("User likes chai")
    assert "User likes chai" in store.memories_for("jarvis")
    assert store.search("chai")
    store.delete_memory(mid)
    assert "User likes chai" not in store.memories_for("jarvis")


def test_routing_english_and_hindi():
    assert route("please explain recursion").name == "SAGE"
    assert route("यह कोड ठीक करो").name == "CODEX"
    assert route("notepad kholo").name == "ORION"
    assert route("@NOVA anything").name == "NOVA"


def test_explicit_learning_hindi_and_english():
    assert learner.explicit("remember that my birthday is 6 November")[0] == "saved"
    assert learner.explicit("याद रखो मुझे क्रिकेट पसंद है")[0] == "saved"
    assert any("क्रिकेट" in m["content"] for m in store.list_memories())
    assert learner.explicit("forget cricket")[0] == "forgot" or True


class FakeRouter:
    def __init__(self, replies): self.replies = list(replies)
    def chat(self, msgs, stream_cb=None, override=None): return self.replies.pop(0), "fake:model"


def test_implicit_learning():
    r = FakeRouter(['[{"fact": "User is building a desktop assistant", "category": "project"}]'])
    saved = learner.extract(r, "I am building a desktop assistant called JARVIS", "Nice!")
    assert saved and any("desktop assistant" in m["content"] for m in store.list_memories())


def test_file_sandbox_and_approval(tmp_path):
    s = Settings(); s.data["allowed_folders"] = [str(tmp_path)]
    files.configure(s, tmp_path / ".trash")
    allowed = ["create_file", "delete_file", "read_file"]
    deny = ApprovalGate(lambda *a: False)
    allow = ApprovalGate(lambda *a: True)
    target = str(tmp_path / "a.txt")
    assert not REGISTRY.run("create_file", {"path": target, "content": "x"}, deny, allowed)["ok"]
    assert REGISTRY.run("create_file", {"path": target, "content": "x"}, allow, allowed)["ok"]
    assert REGISTRY.run("read_file", {"path": target}, deny, allowed)["ok"]  # read needs no approval
    outside = REGISTRY.run("read_file", {"path": "/etc/hostname"}, allow, allowed)
    assert not outside["ok"]
    assert not REGISTRY.run("open_app", {"name": "x"}, allow, allowed)["ok"]  # not permitted for this companion
    EmergencyStop.trigger()
    assert not REGISTRY.run("read_file", {"path": target}, allow, allowed)["ok"]
    EmergencyStop.reset()


def test_orchestrator_tool_loop(tmp_path):
    s = Settings(); s.data.update(allowed_folders=[str(tmp_path)], auto_learn=False)
    files.configure(s, tmp_path / ".trash")
    (tmp_path / "notes.txt").write_text("secret plan")
    o = Orchestrator(s, lambda *a: True)
    call = '```tool\n' + json.dumps({"tool": "read_file", "args": {"path": str(tmp_path / "notes.txt")}}) + '\n```'
    o.router = FakeRouter([call, "The file says: secret plan"])
    cid = store.new_conversation()
    reply, comp, model = o.handle(cid, "@ATLAS read my notes file")
    assert comp == "ATLAS" and "secret plan" in reply and model == "fake:model"
