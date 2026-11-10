"""JARVIS AI — one codebase for Windows 11 and Linux."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


class AppContext:
    def __init__(self, window_provider):
        from storage.settings import Settings
        from storage import db
        from storage.paths import sub
        from backend.orchestrator import Orchestrator
        from workflows.scheduler import WorkflowEngine
        from integrations.base import load_connectors
        import tools.files as files
        import tools.desktop as desktop
        import tools.browser as browser

        db.init()
        self.settings = Settings()
        files.configure(self.settings, sub("trash"))
        desktop.configure(self.settings)
        browser.configure(self.settings)
        self.orchestrator = Orchestrator(self.settings, lambda *a: window_provider().ask_approval(*a))
        connectors = load_connectors(self.settings)
        self.orchestrator.extra_tools = [t for c in connectors for t in c.tools]
        self.workflows = WorkflowEngine(self.orchestrator.run_headless)


def main():
    from backend.lifecycle import setup_logging
    setup_logging()
    # Software OpenGL fallback for old integrated GPUs: set JARVIS_SOFTWARE_GL=1
    if os.environ.get("JARVIS_SOFTWARE_GL"):
        os.environ["QT_QUICK_BACKEND"] = "software"
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QCoreApplication, Qt
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
    app = QApplication(sys.argv)
    app.setApplicationName("JARVIS AI")
    app.setQuitOnLastWindowClosed(False)
    from desktop.theme import DARK
    app.setStyleSheet(DARK)

    holder = {}
    ctx = AppContext(lambda: holder["w"])
    from desktop.main_window import MainWindow
    w = MainWindow(ctx)
    holder["w"] = w
    ctx.workflows.start()

    def on_quit():
        w._quitting = True
        ctx.workflows.shutdown()
    app.aboutToQuit.connect(on_quit)
    if not (w.tray and w.tray.isVisible()):
        app.setQuitOnLastWindowClosed(True)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
