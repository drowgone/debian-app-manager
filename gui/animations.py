"""
Animatsiya komponentlari — skanerlash, o'rnatish, o'chirish va yangilash effektlari.

PySide6 QPropertyAnimation, QTimer va QGraphicsOpacityEffect dan foydalanadi.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QVBoxLayout, QHBoxLayout,
    QGraphicsOpacityEffect, QFrame,
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal,
)
from PySide6.QtGui import QFont, QPainter, QColor

from gui.i18n import tr
from gui.theme import colors as theme_colors


# ── Aylanuvchi spinner ───────────────────────────────────────────────────────

class SpinnerWidget(QWidget):
    """Aylanuvchi doira spinner — jarayon davom etayotganini ko'rsatadi."""

    def __init__(self, size: int = 48, color: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._angle = 0
        self._color = QColor(color or theme_colors()["accent"])
        self._dot_count = 12
        self.setFixedSize(size, size)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self._timer.start(80)

    def _rotate(self) -> None:
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2, self.height() / 2
        radius = min(cx, cy) - 4

        for i in range(self._dot_count):
            angle = self._angle + i * (360 / self._dot_count)
            alpha = int(255 * (i + 1) / self._dot_count)
            color = QColor(self._color)
            color.setAlpha(alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            import math
            rad = math.radians(angle)
            x = cx + radius * 0.7 * math.cos(rad) - 3
            y = cy + radius * 0.7 * math.sin(rad) - 3
            painter.drawEllipse(int(x), int(y), 6, 6)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start(80)

    def stop(self) -> None:
        self._timer.stop()


# ── Matnli spinner (emoji o'rniga) ───────────────────────────────────────────

class TextSpinnerLabel(QLabel):
    """Matn bilan birga aylanuvchi spinner."""

    _FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._base_text = text
        self._frame_idx = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("", 13))
        self._update_text()

    def set_text(self, text: str) -> None:
        self._base_text = text
        self._update_text()

    def _next_frame(self) -> None:
        self._frame_idx = (self._frame_idx + 1) % len(self._FRAMES)
        self._update_text()

    def _update_text(self) -> None:
        frame = self._FRAMES[self._frame_idx]
        self.setText(f"{frame}  {self._base_text}" if self._base_text else frame)

    def start(self) -> None:
        if not self._timer.isActive():
            self._timer.start(100)

    def stop(self) -> None:
        self._timer.stop()
        if self._base_text:
            self.setText(self._base_text)
        else:
            self.setText("")


# ── Pulse effekt ─────────────────────────────────────────────────────────────

class PulseAnimator:
    """Widget opacity'sini pulsatsiya qiladi."""

    def __init__(self, widget: QWidget, min_opacity: float = 0.4, duration_ms: int = 900) -> None:
        self._widget = widget
        self._effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"opacity", widget)
        self._anim.setDuration(duration_ms)
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(min_opacity)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutSine)
        self._anim.setLoopCount(-1)
        self._anim.setDirection(QPropertyAnimation.Direction.Forward)

    def start(self) -> None:
        self._anim.start()

    def stop(self) -> None:
        self._anim.stop()
        self._effect.setOpacity(1.0)


# ── Fade animatsiya yordamchisi ───────────────────────────────────────────────

class FadeAnimator:
    """Widgetni sekin ko'rinib/ko'rinmas bo'lish."""

    @staticmethod
    def fade_in(widget: QWidget, duration_ms: int = 400, on_finished=None) -> QPropertyAnimation:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        widget.show()

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()
        # GC dan saqlash
        widget._fade_anim = anim  # type: ignore[attr-defined]
        return anim

    @staticmethod
    def fade_out(widget: QWidget, duration_ms: int = 350, on_finished=None) -> QPropertyAnimation:
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity", widget)
        anim.setDuration(duration_ms)
        anim.setStartValue(effect.opacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        if on_finished:
            anim.finished.connect(on_finished)
        anim.start()
        widget._fade_anim = anim  # type: ignore[attr-defined]
        return anim


# ── Operatsiya overlay ─────────────────────────────────────────────────────────

class OperationOverlay(QFrame):
    """Jadval ustiga tushadigan shaffof overlay — skanerlash va kutilish holati."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("operationOverlay")
        c = theme_colors()
        self.setStyleSheet(f"""
            QFrame#operationOverlay {{
                background-color: {c['overlay_bg']};
                border-radius: 6px;
            }}
        """)
        self.hide()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        self._spinner = SpinnerWidget(size=56)
        layout.addWidget(self._spinner, alignment=Qt.AlignmentFlag.AlignCenter)

        self._label = TextSpinnerLabel(tr("progress.scan"))
        self._label.setStyleSheet(
            f"color: {c['accent']}; font-weight: 600; font-size: 14px;"
        )
        layout.addWidget(self._label, alignment=Qt.AlignmentFlag.AlignCenter)

        self._sub_label = QLabel("")
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sub_label.setStyleSheet(f"color: {c['text_muted']}; font-size: 12px;")
        layout.addWidget(self._sub_label, alignment=Qt.AlignmentFlag.AlignCenter)

    def show_operation(self, message: str, sub_message: str = "", color: str | None = None) -> None:
        color = color or theme_colors()["accent"]
        self._label.set_text(message)
        self._label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        self._sub_label.setText(sub_message)
        self._spinner._color = QColor(color)  # noqa: SLF001
        self._spinner.start()
        self._label.start()
        self.show()
        self.raise_()
        FadeAnimator.fade_in(self, duration_ms=300)

    def hide_operation(self, on_finished=None) -> None:
        self._spinner.stop()
        self._label.stop()

        def _done() -> None:
            self.hide()
            if on_finished:
                on_finished()

        FadeAnimator.fade_out(self, duration_ms=250, on_finished=_done)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())


# ── Animatsiyali progress bar ──────────────────────────────────────────────────

class AnimatedProgressBar(QProgressBar):
    """Rangli gradient bilan animatsiyali progress bar."""

    _gradient_offset = 0

    def __init__(
        self,
        operation: str = "scan",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._operation = operation
        self._offset = 0
        self.setTextVisible(True)
        self.setFixedHeight(22)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        c = theme_colors()
        op_colors = {
            "scan":    (c["accent"], c["accent_hover"], tr("progress.scan")),
            "install": (c["success"], "#26a269", tr("progress.install")),
            "remove":  (c["danger"], c["danger_hover"], tr("progress.remove")),
            "update":  (c["warning"], c["success"], tr("progress.update")),
        }
        primary, secondary, default_text = op_colors.get(operation, op_colors["scan"])
        self._primary = primary
        self._secondary = secondary

        if operation in ("scan", "install", "remove", "update"):
            self.setRange(0, 0)
            self.setFormat(default_text)
        else:
            self.setRange(0, 100)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)
        self._apply_style()

    def _animate(self) -> None:
        self._offset = (self._offset + 3) % 200
        self._apply_style()

    def _apply_style(self) -> None:
        p, s = self._primary, self._secondary
        # offset 0–100 bo'yicha gradient siljiydi
        t = self._offset / 200.0
        mid = max(0.05, min(0.95, t))
        tc = theme_colors()
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {p};
                border-radius: 4px;
                background-color: {tc['surface_alt']};
                text-align: center;
                font-size: 11px;
                font-weight: 600;
                color: {tc['text']};
                min-height: 20px;
            }}
            QProgressBar::chunk {{
                border-radius: 10px;
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {p},
                    stop:{mid:.2f} {s},
                    stop:1 {p}
                );
            }}
        """)

    def set_success(self) -> None:
        self._timer.stop()
        self.setRange(0, 1)
        self.setValue(1)
        self.setFormat(tr("progress.done"))
        c = theme_colors()
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {c['success']};
                border-radius: 4px;
                background-color: {c['success_bg']};
                text-align: center;
                font-size: 11px;
                font-weight: 600;
                color: {c['success_text']};
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {c['success']};
            }}
        """)

    def set_error(self) -> None:
        self._timer.stop()
        self.setRange(0, 1)
        self.setValue(1)
        self.setFormat(tr("progress.error"))
        c = theme_colors()
        self.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {c['danger']};
                border-radius: 4px;
                background-color: {c['danger_bg']};
                text-align: center;
                font-size: 11px;
                font-weight: 600;
                color: {c['danger']};
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {c['danger']};
            }}
        """)

    def stop_animation(self) -> None:
        self._timer.stop()


# ── Operatsiya badge (jadval qatorida) ─────────────────────────────────────────

class OperationBadge(QWidget):
    """Jadval qatoridagi operatsiya holati — spinner + matn."""

    def __init__(
        self,
        operation: str = "remove",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        c = theme_colors()
        op_map = {
            "remove": (c["danger"], tr("progress.remove")),
            "update": (c["success"], tr("progress.update")),
            "install": (c["accent"], tr("progress.install")),
        }
        color, text = op_map.get(operation, (c["accent"], tr("operation.processing")))
        self._spinner = SpinnerWidget(size=20, color=color)
        layout.addWidget(self._spinner)

        label = QLabel(text)
        label.setFont(QFont("", 10, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {color};")
        layout.addWidget(label)

        self._pulse = PulseAnimator(self, min_opacity=0.65, duration_ms=800)
        self._pulse.start()

    def stop(self) -> None:
        self._spinner.stop()
        self._pulse.stop()


# ── Muvaffaqiyat chaqnashi ─────────────────────────────────────────────────────

class SuccessFlash(QWidget):
    """Qisqa vaqtli yashil muvaffaqiyat chaqnashi."""

    finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        c = theme_colors()
        self.setStyleSheet(
            f"background-color: {c['success_bg']}; border-radius: 6px;"
        )
        self.hide()

    def flash(self, duration_ms: int = 600) -> None:
        if self.parentWidget():
            self.setGeometry(self.parentWidget().rect())
        self.show()
        self.raise_()

        effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(effect)

        anim_in = QPropertyAnimation(effect, b"opacity", self)
        anim_in.setDuration(150)
        anim_in.setStartValue(0.0)
        anim_in.setEndValue(1.0)

        anim_out = QPropertyAnimation(effect, b"opacity", self)
        anim_out.setDuration(duration_ms)
        anim_out.setStartValue(1.0)
        anim_out.setEndValue(0.0)

        anim_in.finished.connect(anim_out.start)
        anim_out.finished.connect(self._on_done)
        anim_in.start()
        self._flash_anims = (anim_in, anim_out)

    def _on_done(self) -> None:
        self.hide()
        self.finished.emit()


# ── Overlay konteyner ──────────────────────────────────────────────────────────

class OverlayContainer(QWidget):
    """Jadval ustiga overlay va flash effektlarini boshqaradigan konteyner."""

    def __init__(
        self,
        content: QWidget,
        overlay: OperationOverlay,
        flash: SuccessFlash,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content)
        self._overlay = overlay
        self._flash = flash
        overlay.setParent(self)
        flash.setParent(self)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        r = self.rect()
        self._overlay.setGeometry(r)
        self._flash.setGeometry(r)


# ── Aylanuvchi tugma effekti ───────────────────────────────────────────────────

class RotatingIconButton:
    """Tugma matnidagi emoji/spinner aylanishini boshqaradi."""

    _SPIN_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, button, idle_text: str, busy_text: str) -> None:
        self._button = button
        self._idle_text = idle_text
        self._busy_text = busy_text
        self._frame = 0
        self._timer = QTimer(button)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._button.setEnabled(False)
        self._frame = 0
        self._timer.start(100)

    def stop(self) -> None:
        self._timer.stop()
        self._button.setEnabled(True)
        self._button.setText(self._idle_text)

    def _tick(self) -> None:
        frame = self._SPIN_FRAMES[self._frame % len(self._SPIN_FRAMES)]
        self._frame += 1
        self._button.setText(f"{frame}  {self._busy_text}")
