"""
Per-task panels with direct-launch design buttons.
"""

from __future__ import annotations
from typing import Type
import time as _time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton,
)
from PyQt6.QtCore import QTimer, Qt

from config.tasks_config import load_task_config

# ═════════════════════════════════════════════════════════════════════
# Registry
# ═════════════════════════════════════════════════════════════════════

_PANELS: dict[str, Type] = {}


def register_panel(name: str):
    def decorator(cls):
        _PANELS[name] = cls
        return cls
    return decorator


def get_registered_panels() -> dict[str, Type]:
    return dict(_PANELS)


# ═════════════════════════════════════════════════════════════════════
# Motor SCAN
# ═════════════════════════════════════════════════════════════════════

@register_panel('SCAN')
class MotorPanel(QWidget):
    TASK = 'motor'

    _chrono_running = False
    _chrono_target = 0
    _chrono_start_epoch = 0.0
    _pending_chrono = None

    def __init__(self, menu):
        super().__init__()
        self.menu = menu

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._tick)

        self._build()

        if MotorPanel._pending_chrono is not None:
            target = MotorPanel._pending_chrono
            MotorPanel._pending_chrono = None
            self._start_chrono(target)
        elif MotorPanel._chrono_running:
            self._timer.start()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setSpacing(10)

        # ── Isolated Task ────────────────────────────────────────────
        t1 = QGroupBox("Isolated Task — Main D / Main G / Pied D (36 essais, ~10min)")
        t1l = QHBoxLayout(t1)
        btn = QPushButton("Lancer")
        btn.setObjectName("run")
        btn.clicked.connect(self._run_isolated)
        t1l.addWidget(btn)
        t1l.addStretch()
        lo.addWidget(t1)

        # ── Combined Task ────────────────────────────────────────────
        t2 = QGroupBox("Combined Task — 6 conditions (32 essais/run, ~10min35)")
        t2l = QGridLayout(t2)
        t2l.setSpacing(6)
        for i in range(3):
            btn = QPushButton(f"Run {i+1}")
            btn.setObjectName("run")
            btn.clicked.connect(lambda _, r=i+1: self._run_combined(r))
            t2l.addWidget(btn, 0, i)
        lo.addWidget(t2)

        # ── Chrono ───────────────────────────────────────────────────
        chrono = QGroupBox("Chronometre repos inter-run")
        cl = QVBoxLayout(chrono)
        cl.setSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_90 = QPushButton("1min30")
        self._btn_90.setObjectName("run")
        self._btn_90.setFixedHeight(36)
        self._btn_90.clicked.connect(lambda: self._start_chrono(90))
        btn_row.addWidget(self._btn_90)

        self._btn_120 = QPushButton("2min00")
        self._btn_120.setObjectName("run")
        self._btn_120.setFixedHeight(36)
        self._btn_120.clicked.connect(lambda: self._start_chrono(120))
        btn_row.addWidget(self._btn_120)

        self._btn_stop = QPushButton("Stop")
        self._btn_stop.setObjectName("resetBtn")
        self._btn_stop.setFixedHeight(36)
        self._btn_stop.clicked.connect(self._stop_chrono)
        btn_row.addWidget(self._btn_stop)

        cl.addLayout(btn_row)

        self._chrono_display = QLabel("--:--.-")
        self._chrono_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chrono_display.setStyleSheet(
            "font-size: 36px; font-weight: bold; "
            "font-family: monospace; padding: 10px; "
            "color: #808080;"
        )
        cl.addWidget(self._chrono_display)

        self._chrono_status = QLabel("")
        self._chrono_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._chrono_status.setStyleSheet(
            "font-size: 12px; color: #808080; padding: 2px;"
        )
        cl.addWidget(self._chrono_status)

        lo.addWidget(chrono)
        lo.addStretch()

    def _run_isolated(self):
        MotorPanel._pending_chrono = None
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': 1,
        })

    def _run_combined(self, run_num):
        if run_num < 3:
            MotorPanel._pending_chrono = 120
        else:
            MotorPanel._pending_chrono = None
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': run_num + 1,
        })

    def _start_chrono(self, target_seconds):
        MotorPanel._chrono_running = True
        MotorPanel._chrono_target = target_seconds
        MotorPanel._chrono_start_epoch = _time.time()

        self._chrono_display.setStyleSheet(
            "font-size: 36px; font-weight: bold; "
            "font-family: monospace; padding: 10px; color: #e0e0e0;"
        )
        t_str = f"{target_seconds // 60}min{target_seconds % 60:02d}s"
        self._chrono_status.setText(f"Repos en cours — cible: {t_str}")
        self._chrono_status.setStyleSheet(
            "font-size: 12px; color: #e08000; padding: 2px;"
        )
        self._timer.start()

    def _stop_chrono(self):
        MotorPanel._chrono_running = False
        MotorPanel._pending_chrono = None
        self._timer.stop()
        self._chrono_display.setText("--:--.-")
        self._chrono_display.setStyleSheet(
            "font-size: 36px; font-weight: bold; "
            "font-family: monospace; padding: 10px; color: #808080;"
        )
        self._chrono_status.setText("")

    def _tick(self):
        if not MotorPanel._chrono_running:
            self._timer.stop()
            return

        elapsed_s = _time.time() - MotorPanel._chrono_start_epoch
        target = MotorPanel._chrono_target

        mins = int(elapsed_s) // 60
        secs = int(elapsed_s) % 60
        tenths = int((elapsed_s % 1) * 10)

        self._chrono_display.setText(f"{mins:02d}:{secs:02d}.{tenths}")

        remaining = target - elapsed_s

        if remaining <= 0:
            self._chrono_display.setStyleSheet(
                "font-size: 36px; font-weight: bold; "
                "font-family: monospace; padding: 10px; color: #00c000;"
            )
            over = int(elapsed_s - target)
            self._chrono_status.setText(f"PRET — termine depuis {over}s")
            self._chrono_status.setStyleSheet(
                "font-size: 12px; color: #00c000; padding: 2px; font-weight: bold;"
            )
        else:
            r_min = int(remaining) // 60
            r_sec = int(remaining) % 60
            self._chrono_status.setText(f"Reste: {r_min:02d}:{r_sec:02d}")