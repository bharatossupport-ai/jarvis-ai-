"""Hosts the 3D companion (Qt Quick 3D). Falls back to a 2D animated orb if 3D is unavailable."""
import math
from PySide6.QtCore import QObject, Property, Signal, QTimer, Qt, QUrl
from PySide6.QtGui import QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget, QVBoxLayout
from companions.profiles import COMPANIONS
from storage.paths import resource


class CompanionBridge(QObject):
    changed = Signal()

    def __init__(self):
        super().__init__()
        self._name, self._mood, self._level = "JARVIS", "idle", 0.0

    def _get_name(self): return self._name
    def _get_color(self): return QColor(COMPANIONS[self._name].color)
    def _get_mood(self): return self._mood
    def _get_level(self): return self._level
    def _get_others(self): return [c.color for n, c in COMPANIONS.items() if n != self._name]

    name = Property(str, _get_name, notify=changed)
    color = Property(QColor, _get_color, notify=changed)
    mood = Property(str, _get_mood, notify=changed)
    level = Property(float, _get_level, notify=changed)
    others = Property("QVariantList", _get_others, notify=changed)

    def set_companion(self, name):
        if name in COMPANIONS:
            self._name = name
            self.changed.emit()

    def set_mood(self, mood):
        self._mood = mood
        self.changed.emit()

    def set_level(self, v):
        self._level = max(0.0, min(1.0, v))
        self.changed.emit()


class Orb2D(QWidget):
    """Fallback for GPUs without Quick 3D support."""

    def __init__(self, bridge):
        super().__init__()
        self.bridge, self.t = bridge, 0.0
        self.timer = QTimer(self, interval=33, timeout=self._tick)
        self.timer.start()

    def _tick(self):
        self.t += 0.05
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#0B0F17"))
        c = self.rect().center()
        b = self.bridge
        speed = 3 if b.mood in ("thinking", "listening") else 1
        r = min(self.width(), self.height()) * 0.18 * (1 + 0.08 * math.sin(self.t * speed) + b.level * 0.3)
        g = QRadialGradient(c, r * 1.8)
        col = b.color
        g.setColorAt(0, col)
        g.setColorAt(0.55, QColor(col.red(), col.green(), col.blue(), 90))
        g.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(g)
        p.setPen(Qt.NoPen)
        p.drawEllipse(c, r * 1.8, r * 1.8)
        for i, oc in enumerate(b.others):
            a = self.t * 0.4 + i / len(b.others) * math.tau
            p.setBrush(QColor(oc))
            p.drawEllipse(c.x() + math.cos(a) * r * 2.6 - 8, c.y() + math.sin(a) * r * 1.1 - 8, 16, 16)
        p.setPen(col)
        p.drawText(self.rect().adjusted(0, 0, 0, -20), Qt.AlignHCenter | Qt.AlignBottom, f"{b.name}  ·  {b.mood.upper()}")


class CompanionView(QWidget):
    def __init__(self, bridge: CompanionBridge, use_3d=True):
        super().__init__()
        self.bridge = bridge
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        widget = None
        if use_3d:
            try:
                from PySide6.QtQuickWidgets import QQuickWidget
                w = QQuickWidget()
                w.setResizeMode(QQuickWidget.SizeRootObjectToView)
                w.rootContext().setContextProperty("bridge", bridge)
                w.setSource(QUrl.fromLocalFile(str(resource("assets/qml/Companion3D.qml"))))
                if w.status() == QQuickWidget.Error:
                    raise RuntimeError("; ".join(e.toString() for e in w.errors()))
                widget = w
            except Exception as e:
                print("3D companion unavailable, using 2D orb:", e)
        self.is_3d = widget is not None
        lay.addWidget(widget or Orb2D(bridge))
