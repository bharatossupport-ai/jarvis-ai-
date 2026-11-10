"""Main window: navigation + all pages."""
import json
import threading
from PySide6.QtCore import QObject, Signal, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QStackedWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QTextBrowser, QPlainTextEdit, QLineEdit, QComboBox, QFrame, QMessageBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QInputDialog, QFormLayout, QCheckBox, QSpinBox, QSystemTrayIcon, QMenu, QApplication,
    QDialog, QDialogButtonBox, QSplitter, QHeaderView)
from companions.profiles import COMPANIONS
from memory import store
from security.policy import EmergencyStop, recent_audit
from storage.settings import set_secret
from storage.paths import resource
from tools.desktop import ADAPTER
from integrations.base import CONNECTORS
from .companion_view import CompanionBridge, CompanionView


# ---------- thread bridge ------------------------------------------------------
class Signals(QObject):
    reply = Signal(str, str, str)       # text, companion, model
    event = Signal(str, str)            # kind, value
    approval = Signal(object)           # request dict with Event
    transcript = Signal(str)
    error = Signal(str)
    speak_done = Signal()


def page(title, subtitle=""):
    w = QWidget(objectName="page")
    lay = QVBoxLayout(w)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.addWidget(QLabel(title, objectName="h1"))
    if subtitle:
        lay.addWidget(QLabel(subtitle, objectName="muted"))
    return w, lay


def card():
    f = QFrame(objectName="card")
    l = QVBoxLayout(f)
    l.setContentsMargins(16, 14, 16, 14)
    return f, l


def fill_table(table, headers, rows):
    table.clear()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            table.setItem(r, c, QTableWidgetItem(str(v)))
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)


class ApprovalDialog(QDialog):
    def __init__(self, parent, req):
        super().__init__(parent)
        self.setWindowTitle("JARVIS needs your approval")
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"<b>{req['tool']}</b>  ·  risk: <b>{req['risk'].upper()}</b>"))
        box = QPlainTextEdit(req["preview"])
        box.setReadOnly(True)
        lay.addWidget(box)
        lay.addWidget(QLabel("Approval covers exactly this action and these parameters.", objectName="muted"))
        bb = QDialogButtonBox()
        bb.addButton("Approve", QDialogButtonBox.AcceptRole)
        bb.addButton("Deny", QDialogButtonBox.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(520, 340)


# ---------- main window ----------------------------------------------------------
class MainWindow(QMainWindow):
    PAGES = ["Home", "Chat", "Companions", "Memory", "Workflows", "PC Control",
             "Integrations", "Activity", "Voice", "Settings"]

    def __init__(self, app_ctx):
        super().__init__()
        self.ctx = app_ctx
        self.settings = app_ctx.settings
        self.sig = Signals()
        self.conv_id = None
        self.companion = "JARVIS"
        self.busy = False
        self.bridge = CompanionBridge()

        self.setWindowTitle("JARVIS AI")
        self.resize(1200, 760)
        icon = resource("assets/jarvis.png")
        if icon.exists():
            self.setWindowIcon(QIcon(str(icon)))

        root = QWidget()
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        self.nav = QListWidget(objectName="nav")
        self.nav.setFixedWidth(190)
        self.nav.addItems(self.PAGES)
        self.stack = QStackedWidget()
        h.addWidget(self.nav)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        builders = [self._home, self._chat, self._companions, self._memory, self._workflows,
                    self._pc_control, self._integrations, self._activity, self._voice, self._settings]
        for b in builders:
            self.stack.addWidget(b())
        self.nav.currentRowChanged.connect(self._on_nav)
        self.nav.setCurrentRow(0)

        self.status_model = QLabel()
        self.statusBar().addPermanentWidget(self.status_model)
        stop = QPushButton("⛔ Emergency stop", objectName="danger")
        stop.clicked.connect(self.emergency_stop)
        self.statusBar().addPermanentWidget(stop)
        QShortcut(QKeySequence("Ctrl+Shift+X"), self, activated=self.emergency_stop)

        self.sig.reply.connect(self._on_reply)
        self.sig.event.connect(self._on_event)
        self.sig.approval.connect(self._on_approval)
        self.sig.transcript.connect(self._on_transcript)
        self.sig.error.connect(lambda e: QMessageBox.warning(self, "JARVIS", e))
        self.sig.speak_done.connect(lambda: self.bridge.set_mood("idle"))

        self._setup_tray()
        self.check_model()
        self.load_conversations()

    # ---- approvals (called from worker threads) ----
    def ask_approval(self, tool, args, risk, preview):
        req = {"tool": tool, "args": args, "risk": risk.value, "preview": preview,
               "done": threading.Event(), "ok": False}
        self.sig.approval.emit(req)
        req["done"].wait()
        return req["ok"]

    def _on_approval(self, req):
        self.showNormal()
        self.raise_()
        req["ok"] = ApprovalDialog(self, req).exec() == QDialog.Accepted
        req["done"].set()

    def emergency_stop(self):
        EmergencyStop.trigger()
        self.statusBar().showMessage("Emergency stop: all actions halted.", 6000)
        self.bridge.set_mood("idle")

    # ---- tray ----
    def _setup_tray(self):
        self.tray = None
        if not (self.settings.get("tray_enabled") and QSystemTrayIcon.isSystemTrayAvailable()):
            return
        self.tray = QSystemTrayIcon(self.windowIcon() or QIcon(), self)
        m = QMenu()
        m.addAction("Show JARVIS", self.showNormal)
        m.addAction("Emergency stop", self.emergency_stop)
        m.addAction("Quit", QApplication.quit)
        self.tray.setContextMenu(m)
        self.tray.activated.connect(lambda r: self.showNormal() if r == QSystemTrayIcon.Trigger else None)
        self.tray.show()

    def _on_nav(self, i):
        self.stack.setCurrentIndex(i)
        refresh = {0: self.refresh_home, 3: self.refresh_memory, 4: self.refresh_workflows, 7: self.refresh_activity}
        if i in refresh:
            refresh[i]()

    # ======================= pages =======================
    def _home(self):
        w, lay = page("Good to see you.", "JARVIS: one brain, many companions, controlled action.")
        row = QHBoxLayout()
        self.home_status, l1 = card()
        self.home_model_lbl = QLabel()
        l1.addWidget(QLabel("<b>Model</b>"))
        l1.addWidget(self.home_model_lbl)
        c2, l2 = card()
        l2.addWidget(QLabel("<b>PC control on this system</b>"))
        l2.addWidget(QLabel(f"{ADAPTER.name}: " + (", ".join(sorted(ADAPTER.capabilities)) or "none")))
        row.addWidget(self.home_status)
        row.addWidget(c2)
        lay.addLayout(row)
        split = QSplitter()
        self.home_view = CompanionView(self.bridge, self.settings.get("show_3d_companion"))
        self.home_view.setMinimumHeight(280)
        split.addWidget(self.home_view)
        c3, l3 = card()
        l3.addWidget(QLabel("<b>Recent tasks</b>"))
        self.home_tasks = QListWidget()
        l3.addWidget(self.home_tasks)
        split.addWidget(c3)
        split.setSizes([600, 400])
        lay.addWidget(split, 1)
        go = QPushButton("Start chatting")
        go.clicked.connect(lambda: self.nav.setCurrentRow(1))
        lay.addWidget(go, alignment=Qt.AlignLeft)
        return w

    def refresh_home(self):
        from storage.db import db
        self.home_tasks.clear()
        with db() as c:
            for r in c.execute("SELECT title, status, companion FROM tasks ORDER BY id DESC LIMIT 12"):
                self.home_tasks.addItem(f"[{r['status']}] {r['companion']}: {r['title']}")

    def _chat(self):
        w, lay = page("Chat", "Type @NOVA, @CODEX, @ATLAS, @ORION, @ECHO or @SAGE to pick a specialist.")
        split = QSplitter()
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        self.conv_list = QListWidget()
        self.conv_list.itemClicked.connect(lambda it: self.open_conversation(it.data(Qt.UserRole)))
        ll.addWidget(self.conv_list)
        b = QHBoxLayout()
        for text, fn in [("New", self.new_conversation), ("Export", self.export_conversation),
                         ("Delete", self.delete_conversation)]:
            btn = QPushButton(text, objectName="ghost")
            btn.clicked.connect(fn)
            b.addWidget(btn)
        ll.addLayout(b)
        split.addWidget(left)

        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        top = QHBoxLayout()
        self.comp_pick = QComboBox()
        self.comp_pick.addItems(["Auto (JARVIS routes)"] + [n for n in COMPANIONS if n != "JARVIS"])
        self.comp_pick.currentTextChanged.connect(self._pick_companion)
        self.prov_pick = QComboBox()
        self.prov_pick.addItems(["embedded", "ollama", "cloud"])
        self.prov_pick.setCurrentText(self.settings.get("provider"))
        self.prov_pick.currentTextChanged.connect(lambda v: (self.settings.set("provider", v), self.check_model()))
        top.addWidget(QLabel("Companion"))
        top.addWidget(self.comp_pick)
        top.addWidget(QLabel("Provider"))
        top.addWidget(self.prov_pick)
        top.addStretch()
        rl.addLayout(top)
        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(True)
        rl.addWidget(self.chat_view, 1)
        self.thinking = QLabel("", objectName="muted")
        rl.addWidget(self.thinking)
        inp = QHBoxLayout()
        self.chat_input = QLineEdit(placeholderText="Ask JARVIS anything… / कुछ भी पूछिए…")
        self.chat_input.returnPressed.connect(self.send)
        self.ptt = QPushButton("🎤 Hold to talk", objectName="ghost")
        self.ptt.pressed.connect(self.ptt_start)
        self.ptt.released.connect(self.ptt_stop)
        send = QPushButton("Send")
        send.clicked.connect(self.send)
        remember = QPushButton("Remember…", objectName="ghost")
        remember.clicked.connect(self.remember_dialog)
        inp.addWidget(self.chat_input, 1)
        inp.addWidget(self.ptt)
        inp.addWidget(remember)
        inp.addWidget(send)
        rl.addLayout(inp)
        split.addWidget(right)
        split.setSizes([260, 900])
        lay.addWidget(split, 1)
        return w

    def _companions(self):
        w, lay = page("Companions", "Specialists share one model. Each has its own tools and memory scope.")
        split = QSplitter()
        self.comp_view = CompanionView(self.bridge, self.settings.get("show_3d_companion"))
        split.addWidget(self.comp_view)
        lst = QListWidget()
        for c in COMPANIONS.values():
            lst.addItem(f"{c.name} — {c.role}\n   tools: {', '.join(c.tools)}")
        lst.currentRowChanged.connect(lambda i: self.bridge.set_companion(list(COMPANIONS)[i]))
        split.addWidget(lst)
        split.setSizes([650, 450])
        lay.addWidget(split, 1)
        lay.addWidget(QLabel("3D view: " + ("Qt Quick 3D" if self.comp_view.is_3d else "2D fallback (3D not supported by this GPU/driver)"),
                             objectName="muted"))
        return w

    def _memory(self):
        w, lay = page("Memory", "Everything JARVIS remembers is visible, editable and deletable here.")
        row = QHBoxLayout()
        self.mem_search = QLineEdit(placeholderText="Search memory, chats and documents…")
        self.mem_search.returnPressed.connect(self.do_search)
        row.addWidget(self.mem_search, 1)
        for text, fn in [("Add", self.remember_dialog), ("Approve", self.approve_mem), ("Edit", self.edit_mem),
                         ("Delete", self.delete_mem), ("Add document", self.add_doc), ("Export all", self.export_mem)]:
            b = QPushButton(text, objectName="ghost")
            b.clicked.connect(fn)
            row.addWidget(b)
        lay.addLayout(row)
        self.mem_table = QTableWidget()
        self.mem_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.mem_table, 1)
        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(160)
        lay.addWidget(self.search_results)
        return w

    def _workflows(self):
        w, lay = page("Workflows", "Prompts that run on a schedule. Risky actions still ask for approval.")
        row = QHBoxLayout()
        for text, fn in [("New workflow", self.new_workflow), ("Run now", self.run_workflow),
                         ("Pause", lambda: self._wf_act("pause")), ("Resume", lambda: self._wf_act("resume")),
                         ("Delete", lambda: self._wf_act("delete"))]:
            b = QPushButton(text, objectName="ghost" if text != "New workflow" else "")
            b.clicked.connect(fn)
            row.addWidget(b)
        row.addStretch()
        lay.addLayout(row)
        self.wf_table = QTableWidget()
        self.wf_table.setSelectionBehavior(QTableWidget.SelectRows)
        lay.addWidget(self.wf_table, 1)
        lay.addWidget(QLabel("<b>Run history</b>"))
        self.wf_runs = QTableWidget()
        lay.addWidget(self.wf_runs, 1)
        return w

    def _pc_control(self):
        w, lay = page("PC Control", "ORION can only open apps and touch folders you allow here.")
        c, l = card()
        l.addWidget(QLabel(f"<b>System:</b> {ADAPTER.name}  ·  available: {', '.join(sorted(ADAPTER.capabilities))}"))
        if ADAPTER.name == "linux" and getattr(ADAPTER, "session", "") != "x11":
            l.addWidget(QLabel("You're on Wayland: window control is limited. Log in with an X11 session for full control.",
                               objectName="muted"))
        lay.addWidget(c)
        lay.addWidget(QLabel("<b>Allowed apps</b> (name → command)"))
        self.apps_list = QListWidget()
        lay.addWidget(self.apps_list)
        r = QHBoxLayout()
        a = QPushButton("Add app")
        a.clicked.connect(self.add_app)
        d = QPushButton("Remove", objectName="ghost")
        d.clicked.connect(self.remove_app)
        r.addWidget(a)
        r.addWidget(d)
        r.addStretch()
        lay.addLayout(r)
        lay.addWidget(QLabel("<b>Allowed folders</b> (ATLAS file tools)"))
        self.folders_list = QListWidget()
        lay.addWidget(self.folders_list)
        r2 = QHBoxLayout()
        af = QPushButton("Add folder")
        af.clicked.connect(self.add_folder)
        rf = QPushButton("Remove", objectName="ghost")
        rf.clicked.connect(self.remove_folder)
        r2.addWidget(af)
        r2.addWidget(rf)
        r2.addStretch()
        lay.addLayout(r2)
        self.refresh_allowlists()
        return w

    def _integrations(self):
        w, lay = page("Integrations", "Connectors add tools. Enable only what you use. Restart to apply.")
        enabled = set(self.settings.get("enabled_connectors") or [])
        self.conn_checks = {}
        for name, cls in CONNECTORS.items():
            c, l = card()
            cb = QCheckBox(f"{name} — {cls.description}")
            cb.setChecked(name in enabled)
            cb.toggled.connect(self._save_connectors)
            self.conn_checks[name] = cb
            l.addWidget(cb)
            lay.addWidget(c)
        form = QFormLayout()
        self.webhook = QLineEdit(self.settings.get("webhook_url") or "")
        self.webhook.editingFinished.connect(lambda: self.settings.set("webhook_url", self.webhook.text().strip()))
        form.addRow("Webhook URL", self.webhook)
        lay.addLayout(form)
        lay.addWidget(QLabel("Browser automation (NOVA) uses its own JARVIS browser profile, never your main one.",
                             objectName="muted"))
        lay.addStretch()
        return w

    def _activity(self):
        w, lay = page("Activity", "Audit log of every tool call, approval and error.")
        b = QPushButton("Refresh", objectName="ghost")
        b.clicked.connect(self.refresh_activity)
        lay.addWidget(b, alignment=Qt.AlignLeft)
        self.audit_table = QTableWidget()
        lay.addWidget(self.audit_table, 1)
        return w

    def _voice(self):
        w, lay = page("Voice", "Push-to-talk only. The mic is on only while you hold the button.")
        form = QFormLayout()
        from voice.speech import list_input_devices
        self.mic = QComboBox()
        self.mic.addItem("System default", None)
        for i, name in list_input_devices():
            self.mic.addItem(name, i)
        self.mic.currentIndexChanged.connect(lambda _: self.settings.set("mic_device", self.mic.currentData()))
        form.addRow("Microphone", self.mic)
        self.whisper = QComboBox()
        self.whisper.addItems(["tiny", "base", "small"])
        self.whisper.setCurrentText(self.settings.get("whisper_model"))
        self.whisper.currentTextChanged.connect(lambda v: self.settings.set("whisper_model", v))
        form.addRow("Whisper model", self.whisper)
        self.vlang = QComboBox()
        for label, code in [("Auto-detect (Hindi + English)", "auto"), ("Hindi", "hi"), ("English", "en")]:
            self.vlang.addItem(label, code)
        self.vlang.setCurrentIndex(max(0, self.vlang.findData(self.settings.get("voice_language"))))
        self.vlang.currentIndexChanged.connect(lambda _: self.settings.set("voice_language", self.vlang.currentData()))
        form.addRow("Spoken language", self.vlang)
        form.addRow("", QLabel("Built-in voices: Hindi (pratham) and English (lessac), picked automatically. Leave the voice path empty to use them.", objectName="muted"))
        vrow = QHBoxLayout()
        self.piper_path = QLineEdit(self.settings.get("piper_voice"))
        pick = QPushButton("Browse", objectName="ghost")
        pick.clicked.connect(self.pick_voice)
        vrow.addWidget(self.piper_path)
        vrow.addWidget(pick)
        form.addRow("Piper voice (.onnx)", vrow)
        self.speak = QCheckBox("Speak replies aloud")
        self.speak.setChecked(self.settings.get("speak_replies"))
        self.speak.toggled.connect(lambda v: self.settings.set("speak_replies", v))
        form.addRow("", self.speak)
        lay.addLayout(form)
        self.rec_indicator = QLabel("● Mic off", objectName="muted")
        lay.addWidget(self.rec_indicator)
        lay.addStretch()
        return w

    def _settings(self):
        w, lay = page("Settings")
        form = QFormLayout()
        self.f = {}
        mp = QLineEdit(self.settings.get("embedded_model_path") or "")
        mp.setPlaceholderText("Empty = built-in Hermes 3 (3B)")
        mp.editingFinished.connect(lambda: (self.settings.set("embedded_model_path", mp.text().strip()), self.check_model()))
        form.addRow("Built-in model file (.gguf)", mp)
        for key, label in [("ollama_url", "Ollama URL"), ("ollama_model", "Ollama model"),
                           ("cloud_base_url", "Cloud API base URL"), ("cloud_model", "Cloud model")]:
            e = QLineEdit(str(self.settings.get(key)))
            e.editingFinished.connect(lambda k=key, e=e: (self.settings.set(k, e.text().strip()), self.check_model()))
            form.addRow(label, e)
            self.f[key] = e
        key_btn = QPushButton("Set cloud API key (stored in OS keyring)", objectName="ghost")
        key_btn.clicked.connect(self.set_api_key)
        form.addRow("", key_btn)
        to = QSpinBox()
        to.setRange(10, 600)
        to.setValue(int(self.settings.get("request_timeout")))
        to.valueChanged.connect(lambda v: self.settings.set("request_timeout", v))
        form.addRow("Request timeout (s)", to)
        ctxn = QSpinBox()
        ctxn.setRange(4, 100)
        ctxn.setValue(int(self.settings.get("max_context_messages")))
        ctxn.valueChanged.connect(lambda v: self.settings.set("max_context_messages", v))
        form.addRow("Messages kept in context", ctxn)
        lang = QComboBox()
        for label, code in [("Match my language (Hindi / English / Hinglish)", "auto"), ("Always Hindi", "hi"), ("Always English", "en")]:
            lang.addItem(label, code)
        lang.setCurrentIndex(max(0, lang.findData(self.settings.get("language"))))
        lang.currentIndexChanged.connect(lambda _: self.settings.set("language", lang.currentData()))
        form.addRow("Reply language", lang)
        for key, label in [("show_3d_companion", "Show 3D companion (restart)"), ("tray_enabled", "Tray icon (restart)"),
                           ("browser_headless", "Run browser hidden"),
                           ("auto_learn", "Learn from my chats"),
                           ("auto_approve_learned", "Use learned facts right away (off = I approve each one)")]:
            cb = QCheckBox(label)
            cb.setChecked(bool(self.settings.get(key)))
            cb.toggled.connect(lambda v, k=key: self.settings.set(k, v))
            form.addRow("", cb)
        lay.addLayout(form)
        row = QHBoxLayout()
        bk = QPushButton("Back up data…", objectName="ghost")
        bk.clicked.connect(self.backup)
        rs = QPushButton("Restore backup…", objectName="ghost")
        rs.clicked.connect(self.restore)
        row.addWidget(bk)
        row.addWidget(rs)
        row.addStretch()
        lay.addLayout(row)
        lay.addStretch()
        return w

    # ======================= chat logic =======================
    def check_model(self):
        def work():
            ok, info = self.ctx.orchestrator.router.provider().status()
            p = self.ctx.orchestrator.router.provider()
            label = f"{'🟢' if ok else '🔴'} {p.name}: {p.model}"
            if not ok:
                label += "  (not reachable)"
            self.sig.event.emit("model", label)
        threading.Thread(target=work, daemon=True).start()

    def load_conversations(self):
        self.conv_list.clear()
        convs = store.list_conversations()
        for c in convs:
            from PySide6.QtWidgets import QListWidgetItem
            it = QListWidgetItem(c["title"])
            it.setData(Qt.UserRole, c["id"])
            self.conv_list.addItem(it)
        if convs and self.conv_id is None:
            self.open_conversation(convs[0]["id"])
        elif not convs:
            self.new_conversation()

    def new_conversation(self):
        self.conv_id = store.new_conversation()
        self.chat_view.clear()
        self.load_conversations()

    def open_conversation(self, cid):
        self.conv_id = cid
        self.chat_view.clear()
        for m in store.messages(cid):
            self._append(m["role"], m["content"], m.get("companion") or "JARVIS", m.get("model") or "")

    def delete_conversation(self):
        if self.conv_id and QMessageBox.question(self, "Delete", "Delete this conversation permanently?") == QMessageBox.Yes:
            store.delete_conversation(self.conv_id)
            self.conv_id = None
            self.load_conversations()

    def export_conversation(self):
        if not self.conv_id:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export", "conversation.json", "JSON (*.json)")
        if path:
            store.export_conversation(self.conv_id, path)

    def _pick_companion(self, text):
        self.companion = "JARVIS" if text.startswith("Auto") else text
        self.bridge.set_companion(self.companion)

    def _append(self, role, text, companion, model=""):
        import html
        color = COMPANIONS.get(companion, COMPANIONS["JARVIS"]).color
        safe = html.escape(text).replace("\n", "<br>")
        if role == "user":
            self.chat_view.append(f"<p style='margin:10px 0'><b style='color:#8B98A5'>You</b><br>{safe}</p>")
        else:
            tag = f" <span style='color:#5C6773;font-size:11px'>· {model}</span>" if model else ""
            self.chat_view.append(f"<p style='margin:10px 0'><b style='color:{color}'>{companion}</b>{tag}<br>{safe}</p>")

    def send(self, text=None):
        text = (text or self.chat_input.text()).strip()
        if not text or self.busy:
            return
        if self.conv_id is None:
            self.new_conversation()
        self.chat_input.clear()
        self.busy = True
        self._append("user", text, "JARVIS")
        self.thinking.setText("Thinking…")
        self.bridge.set_mood("thinking")
        cid, comp = self.conv_id, self.companion

        def work():
            try:
                reply, c, model = self.ctx.orchestrator.handle(
                    cid, text, comp, on_event=lambda k, v: self.sig.event.emit(k, v))
                self.sig.reply.emit(reply, c, model)
            except Exception as e:
                self.sig.reply.emit(f"⚠ Unexpected error: {e}", comp, "")
        threading.Thread(target=work, daemon=True).start()

    def _on_event(self, kind, value):
        if kind == "model":
            self.status_model.setText(value)
            self.home_model_lbl.setText(value)
        elif kind == "companion":
            self.bridge.set_companion(value)
            self.thinking.setText(f"{value} is working…")
        elif kind == "tool":
            self.thinking.setText(f"Using tool: {value}")
        elif kind == "learned":
            self.chat_view.append(f"<p style='color:#5C6773;font-size:11px'>🧠 Learned: {value}</p>")
            self.statusBar().showMessage(f"Learned: {value}", 5000)
        elif kind == "forgot":
            self.chat_view.append(f"<p style='color:#5C6773;font-size:11px'>🧠 Forgot {value}</p>")

    def _on_reply(self, text, companion, model):
        self.busy = False
        self.thinking.setText("")
        self._append("assistant", text, companion, model)
        self.load_conversations()
        if self.settings.get("speak_replies"):
            self.speak_text(text)
        else:
            self.bridge.set_mood("idle")

    # ======================= voice =======================
    def ptt_start(self):
        from voice.speech import Recorder
        try:
            self.recorder = Recorder(self.settings.get("mic_device"))
            self.recorder.start()
            self.bridge.set_mood("listening")
            self.ptt.setText("● Recording…")
            self.rec_indicator.setText("● Recording")
        except Exception as e:
            self.sig.error.emit(f"Microphone error: {e}")

    def ptt_stop(self):
        self.ptt.setText("🎤 Hold to talk")
        self.rec_indicator.setText("● Mic off")
        rec = getattr(self, "recorder", None)
        if not rec or not rec.recording:
            return
        audio = rec.stop()
        self.bridge.set_mood("thinking")

        def work():
            from voice.speech import Transcriber
            try:
                self.sig.transcript.emit(Transcriber(self.settings.get("whisper_model"),
                                                     self.settings.get("voice_language")).transcribe(audio))
            except Exception as e:
                self.sig.error.emit(f"Transcription failed: {e}")
                self.sig.transcript.emit("")
        threading.Thread(target=work, daemon=True).start()

    def _on_transcript(self, text):
        if text:
            self.send(text)
        else:
            self.bridge.set_mood("idle")

    def speak_text(self, text):
        self.bridge.set_mood("speaking")

        def work():
            try:
                import numpy as np
                import sounddevice as sd
                import soundfile as sf
                from voice.speech import Speaker, looks_hindi
                sp = Speaker(self.settings.get("piper_voice"), "hi" if looks_hindi(text) else "en")
                if not sp.available():
                    raise RuntimeError("No voice found. Pick a Piper voice on the Voice page.")
                wav = sp.synth(text[:1200])
                data, sr = sf.read(wav, dtype="float32")
                block = int(sr * 0.05)
                for i in range(0, len(data), block):
                    if EmergencyStop.active():
                        break
                    chunk = data[i:i + block]
                    self.bridge.set_level(float(np.sqrt(np.mean(chunk ** 2)) * 6))
                    sd.play(chunk, sr, blocking=True)
            except Exception as e:
                self.sig.error.emit(f"Speech failed: {e}")
            finally:
                self.bridge.set_level(0)
                self.sig.speak_done.emit()
        threading.Thread(target=work, daemon=True).start()

    def pick_voice(self):
        p, _ = QFileDialog.getOpenFileName(self, "Piper voice", "", "Piper voice (*.onnx)")
        if p:
            self.piper_path.setText(p)
            self.settings.set("piper_voice", p)

    # ======================= memory =======================
    def remember_dialog(self):
        text, ok = QInputDialog.getMultiLineText(self, "Remember", "What should JARVIS remember?")
        if ok and text.strip():
            cat, ok2 = QInputDialog.getItem(self, "Category", "Category", store.CATEGORIES, 0, False)
            scope, ok3 = QInputDialog.getItem(self, "Who can use it", "Scope",
                                              ["shared"] + [c.lower() for c in COMPANIONS], 0, False)
            if ok2 and ok3:
                store.add_memory(text.strip(), cat, scope)
                self.refresh_memory()

    def refresh_memory(self):
        rows = store.list_memories()
        self._mem_ids = [m["id"] for m in rows]
        fill_table(self.mem_table, ["Content", "Category", "Scope", "Approved", "Created"],
                   [[m["content"], m["category"], m["scope"], "yes" if m["approved"] else "pending", m["created"]] for m in rows])

    def _sel_mem(self):
        r = self.mem_table.currentRow()
        return self._mem_ids[r] if 0 <= r < len(getattr(self, "_mem_ids", [])) else None

    def approve_mem(self):
        if (m := self._sel_mem()):
            store.approve_memory(m)
            self.refresh_memory()

    def edit_mem(self):
        if (m := self._sel_mem()):
            cur = self.mem_table.item(self.mem_table.currentRow(), 0).text()
            t, ok = QInputDialog.getMultiLineText(self, "Edit memory", "Content", cur)
            if ok:
                store.update_memory(m, t)
                self.refresh_memory()

    def delete_mem(self):
        if (m := self._sel_mem()):
            store.delete_memory(m)
            self.refresh_memory()

    def add_doc(self):
        p, _ = QFileDialog.getOpenFileName(self, "Add document to knowledge base", "", "Text (*.txt *.md *.py *.csv *.json)")
        if p:
            store.add_document(p)
            self.statusBar().showMessage(f"Added {p}", 4000)

    def export_mem(self):
        p, _ = QFileDialog.getSaveFileName(self, "Export memory", "jarvis_memory.json", "JSON (*.json)")
        if p:
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"memories": store.list_memories(), "projects": store.list_projects()}, f, indent=2)

    def do_search(self):
        self.search_results.clear()
        for r in store.search(self.mem_search.text()):
            self.search_results.addItem(f"[{r['kind']}] {r['s']}")

    # ======================= workflows =======================
    def refresh_workflows(self):
        eng = self.ctx.workflows
        wfs = eng.list()
        self._wf_ids = [w["id"] for w in wfs]
        fill_table(self.wf_table, ["Name", "Prompt", "Schedule", "Companion", "Status", "Next run"],
                   [[w["name"], w["prompt"], f"{w['trigger']} {w['spec']}", w["companion"],
                     "active" if w["enabled"] else "paused", eng.next_run(w["id"])] for w in wfs])
        runs = eng.runs()
        fill_table(self.wf_runs, ["Workflow", "Status", "Output", "When"],
                   [[r["name"], r["status"], (r["output"] or "")[:120], r["created"]] for r in runs])

    def new_workflow(self):
        name, ok = QInputDialog.getText(self, "New workflow", "Name")
        if not ok or not name:
            return
        prompt, ok = QInputDialog.getMultiLineText(self, "New workflow", "What should JARVIS do each time?")
        if not ok or not prompt:
            return
        kind, ok = QInputDialog.getItem(self, "Schedule", "Type", ["daily", "interval"], 0, False)
        if not ok:
            return
        if kind == "daily":
            t, ok = QInputDialog.getText(self, "Daily", "Time (HH:MM)", text="09:00")
            hh, mm = (t.split(":") + ["0"])[:2]
            spec = {"hour": int(hh), "minute": int(mm)}
        else:
            mins, ok = QInputDialog.getInt(self, "Interval", "Every N minutes", 60, 1, 10080)
            spec = {"minutes": mins}
        comp, ok = QInputDialog.getItem(self, "Companion", "Who runs it", list(COMPANIONS), 0, False)
        self.ctx.workflows.create(name, prompt, "cron" if kind == "daily" else "interval", spec, comp)
        self.refresh_workflows()

    def _sel_wf(self):
        r = self.wf_table.currentRow()
        return self._wf_ids[r] if 0 <= r < len(getattr(self, "_wf_ids", [])) else None

    def _wf_act(self, act):
        if (w := self._sel_wf()):
            getattr(self.ctx.workflows, act)(w)
            self.refresh_workflows()

    def run_workflow(self):
        if (w := self._sel_wf()):
            threading.Thread(target=lambda: self.ctx.workflows.run_now(w), daemon=True).start()
            QTimer.singleShot(1500, self.refresh_workflows)

    # ======================= allowlists / settings =======================
    def refresh_allowlists(self):
        self.apps_list.clear()
        for k, v in (self.settings.get("allowed_apps") or {}).items():
            self.apps_list.addItem(f"{k} → {v}")
        self.folders_list.clear()
        self.folders_list.addItems(self.settings.get("allowed_folders") or [])

    def add_app(self):
        name, ok = QInputDialog.getText(self, "Allow app", "Friendly name (e.g. Notepad, Firefox)")
        if not ok or not name:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Pick the program")
        if not path:
            path, ok = QInputDialog.getText(self, "Allow app", "Or type the command (e.g. firefox, notepad.exe)")
        if path:
            apps = dict(self.settings.get("allowed_apps") or {})
            apps[name] = path
            self.settings.set("allowed_apps", apps)
            self.refresh_allowlists()

    def remove_app(self):
        it = self.apps_list.currentItem()
        if it:
            apps = dict(self.settings.get("allowed_apps") or {})
            apps.pop(it.text().split(" → ")[0], None)
            self.settings.set("allowed_apps", apps)
            self.refresh_allowlists()

    def add_folder(self):
        d = QFileDialog.getExistingDirectory(self, "Allow folder")
        if d:
            self.settings.set("allowed_folders", list(dict.fromkeys((self.settings.get("allowed_folders") or []) + [d])))
            self.refresh_allowlists()

    def remove_folder(self):
        it = self.folders_list.currentItem()
        if it:
            self.settings.set("allowed_folders", [f for f in self.settings.get("allowed_folders") if f != it.text()])
            self.refresh_allowlists()

    def _save_connectors(self):
        self.settings.set("enabled_connectors", [n for n, cb in self.conn_checks.items() if cb.isChecked()])

    def refresh_activity(self):
        rows = recent_audit()
        fill_table(self.audit_table, ["When", "Kind", "Detail"], [[r["created"], r["kind"], r["detail"]] for r in rows])

    def set_api_key(self):
        k, ok = QInputDialog.getText(self, "Cloud API key", "Paste your API key", QLineEdit.Password)
        if ok and k:
            try:
                set_secret("cloud_api_key", k.strip())
                self.check_model()
            except Exception as e:
                QMessageBox.warning(self, "Keyring", f"Couldn't save key: {e}")

    def backup(self):
        from backend.lifecycle import backup
        p, _ = QFileDialog.getSaveFileName(self, "Backup", "jarvis_backup.zip", "Zip (*.zip)")
        if p:
            backup(p)
            self.statusBar().showMessage(f"Backup saved: {p}", 5000)

    def restore(self):
        from backend.lifecycle import restore
        p, _ = QFileDialog.getOpenFileName(self, "Restore", "", "Zip (*.zip)")
        if p and QMessageBox.question(self, "Restore", "Replace current data with this backup? JARVIS will close.") == QMessageBox.Yes:
            restore(p)
            QApplication.quit()

    def closeEvent(self, e):
        if self.tray and self.tray.isVisible() and not getattr(self, "_quitting", False):
            self.hide()
            self.tray.showMessage("JARVIS", "Still running in the tray.", QSystemTrayIcon.Information, 2000)
            e.ignore()
        else:
            e.accept()
