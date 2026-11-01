"""Sobreposicao leve para marcar pontos de clique em monitores multiplos."""
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget, QApplication


class Overlay(QWidget):
    selected = Signal(int, int)
    cancelled = Signal()

    def __init__(self, screen, caption):
        super().__init__(None, Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.caption = caption
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setGeometry(screen.geometry())

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(10, 10, 10, 42))
        p.fillRect(0, 0, self.width(), 48, QColor(24, 25, 29, 230))
        p.setPen(QColor('white'))
        font = p.font()
        font.setPointSize(12)
        font.setBold(True)
        p.setFont(font)
        p.drawText(self.rect().adjusted(14, 0, -14, 0),
                   Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter,
                   f'  {self.caption}: clique no local desejado   |   Esc cancela  ')

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Coordenadas fisicas, iguais as usadas pelo PyAutoGUI.
            try:
                import pyautogui
                x, y = pyautogui.position()
            except Exception:
                point = event.globalPosition().toPoint()
                x, y = point.x(), point.y()
            self.selected.emit(int(x), int(y))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()


class Selector:
    def __init__(self, parent, caption, callback):
        self.parent = parent
        self.callback = callback
        self.overlays = []
        self.completed = False
        self.parent.hide()
        QTimer.singleShot(330, lambda: self.start(caption))

    def start(self, caption):
        if self.completed:
            return
        for screen in QApplication.screens():
            layer = Overlay(screen, caption)
            layer.selected.connect(self.choose)
            layer.cancelled.connect(self.close)
            self.overlays.append(layer)
            layer.show()
        if self.overlays:
            self.overlays[0].activateWindow()

    def choose(self, x, y):
        if self.completed:
            return
        self.completed = True
        self.close()
        self.callback(x, y)

    def close(self):
        self.completed = True
        for layer in self.overlays:
            layer.close()
            layer.deleteLater()
        self.overlays.clear()
        self.parent.show()
        self.parent.raise_()
        self.parent.activateWindow()
