"""
Per-task panels. Direct-launch design buttons.
"""

from __future__ import annotations
from typing import Type

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QLabel, QPushButton, QSpinBox,
)

from config.tasks_config import load_task_config

_PANELS: dict[str, Type] = {}


def register_panel(name: str):
    def decorator(cls):
        _PANELS[name] = cls
        return cls
    return decorator


def get_registered_panels() -> dict[str, Type]:
    return dict(_PANELS)


# ── Helper: builds design button grid from YAML ─────────────────────

def _make_design_group(widget, task_name: str, designs: dict,
                       run_cb) -> QGroupBox:
    group = QGroupBox("Designs")
    g = QGridLayout(group)
    g.setSpacing(6)
    for i, (did, d) in enumerate(sorted(designs.items())):
        name = d.get('name', f'Design {did}')
        btn = QPushButton(f"Design {did}")
        btn.setObjectName("run")
        btn.setToolTip(name)
        btn.clicked.connect(lambda _, d=did: run_cb(d))
        g.addWidget(btn, i // 2, i % 2)
    return group


def _make_training_group(spin_default, run_cb) -> tuple[QGroupBox, QSpinBox]:
    group = QGroupBox("Training")
    h = QHBoxLayout(group)
    h.addWidget(QLabel("Essais/bloc :"))
    spin = QSpinBox()
    spin.setRange(3, 30)
    spin.setValue(spin_default)
    spin.setFixedWidth(55)
    h.addWidget(spin)
    h.addStretch()
    btn = QPushButton("Lancer Training")
    btn.clicked.connect(run_cb)
    h.addWidget(btn)
    return group, spin


# ═════════════════════════════════════════════════════════════════════
# Flanker
# ═════════════════════════════════════════════════════════════════════

@register_panel('Flanker')
class FlankerPanel(QWidget):
    TASK = 'flanker'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        lo.addWidget(_make_design_group(self, self.TASK, self.designs,
                                        self._run))

        grp, self.sp = _make_training_group(10, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'condition': 'congruent',   'n_trials': n},
                    {'condition': 'incongruent', 'n_trials': n},
                    {'condition': 'mixed', 'n_trials': n, 'prop_incongruent': 0.5},
                ],
                'rest_duration': 5.0,
            },
        })


# ═════════════════════════════════════════════════════════════════════
# N-Back
# ═════════════════════════════════════════════════════════════════════

@register_panel('N-Back')
class NBackPanel(QWidget):
    TASK = 'nback'

    DESIGN_INFO = {
        1: ("Compact 0v2",   "~6min",    "8 blocs, 12 essais, rest  6s"),
        2: ("Balanced 0v2",  "~7min",    "10 blocs, 12 essais, rest  7s"),
        3: ("Power 0v2",     "~8min30",  "12 blocs, 14 essais, rest  8s"),
        4: ("Research 0v2",  "~10min",   "14 blocs, 15 essais, rest 10s"),
    }

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        # Design buttons with name + duration
        design_group = QGroupBox("Designs")
        dg = QGridLayout(design_group)
        dg.setSpacing(6)

        for i, (did, _) in enumerate(sorted(self.designs.items())):
            short, dur, desc = self.DESIGN_INFO.get(
                did, (f"Design {did}", "?", "")
            )
            btn = QPushButton(f"D{did}: {short}  [{dur}]")
            btn.setObjectName("run")
            btn.setToolTip(desc)
            btn.clicked.connect(lambda _, d=did: self._run(d))
            dg.addWidget(btn, i // 2, i % 2)

        lo.addWidget(design_group)

        info = QLabel(
            "0-back : appuyer si lettre = cible\n"
            "2-back : appuyer si lettre = celle d'il y a 2\n"
            "Stim 500ms + ISI 1500ms = 2s/essai\n"
            "Contraste : 2-back > 0-back (DLPFC, ACC)"
        )
        info.setStyleSheet("color: #808080; font-size: 11px; padding: 4px;")
        lo.addWidget(info)

        grp, self.sp = _make_training_group(8, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 1,
            'extra_params': {
                'block_sequence': [
                    {'level': 0, 'n_trials': n},
                    {'level': 1, 'n_trials': n},
                    {'level': 2, 'n_trials': n},
                ],
                'rest_duration': 5.0,
            },
        })

# ═════════════════════════════════════════════════════════════════════
# Stroop
# ═════════════════════════════════════════════════════════════════════

@register_panel('Stroop')
class StroopPanel(QWidget):
    TASK = 'stroop'

    DESIGN_INFO = {
        1: ("Initial 15x10",   "~7min20"),
        2: ("Optimise 15x8",   "~5min50"),
        3: ("Compact 12x10",   "~5min30"),
        4: ("Final 9x15",      "~5min25"),
    }

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        # ── Manual designs ───────────────────────────────────────────
        manual_group = QGroupBox("Manuel (boutons)")
        mg = QGridLayout(manual_group)
        mg.setSpacing(6)
        for i, (did, _) in enumerate(sorted(self.designs.items())):
            short, dur = self.DESIGN_INFO.get(did, (f"D{did}", "?"))
            btn = QPushButton(f"D{did}: {short}  [{dur}]")
            btn.setObjectName("run")
            btn.clicked.connect(lambda _, d=did: self._run(d, 'manual'))
            mg.addWidget(btn, i // 2, i % 2)
        lo.addWidget(manual_group)

        # ── Vocal designs ────────────────────────────────────────────
        vocal_group = QGroupBox("Vocal (microphone)")
        vg = QGridLayout(vocal_group)
        vg.setSpacing(6)
        for i, (did, _) in enumerate(sorted(self.designs.items())):
            short, dur = self.DESIGN_INFO.get(did, (f"D{did}", "?"))
            btn = QPushButton(f"D{did}: {short}  [{dur}]")
            btn.setObjectName("run")
            btn.setToolTip("Reponse vocale — enregistrement micro continu")
            btn.clicked.connect(lambda _, d=did: self._run(d, 'vocal'))
            vg.addWidget(btn, i // 2, i % 2)
        lo.addWidget(vocal_group)

        info = QLabel(
            "3 couleurs : ROUGE  BLEU  VERT\n"
            "Neutre : XXXX / %%%% / OOOO\n"
            "Manuel : cercles colores, pas de texte\n"
            "Vocal : dire la couleur, micro enregistre"
        )
        info.setStyleSheet("color: #808080; font-size: 11px; padding: 4px;")
        lo.addWidget(info)

        grp, self.sp = _make_training_group(10, self._train_manual)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did, mode):
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': did,
            'extra_params': {'response_mode': mode},
        })

    def _train_manual(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 4,
            'extra_params': {
                'response_mode': 'manual',
                'block_sequence': [
                    {'condition': 'neutral',     'n_trials': n},
                    {'condition': 'congruent',   'n_trials': n},
                    {'condition': 'incongruent', 'n_trials': n},
                ],
                'rest_duration': 5.0,
            },
        })

# ═════════════════════════════════════════════════════════════════════
# Oddball Auditif
# ═════════════════════════════════════════════════════════════════════

@register_panel('Oddball')
class OddballPanel(QWidget):
    TASK = 'oddball'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        cfg = load_task_config(self.TASK)
        self.designs = cfg.get('designs', {})
        lo = QVBoxLayout(self)
        lo.setSpacing(8)

        lo.addWidget(_make_design_group(self, self.TASK, self.designs,
                                        self._run))

        info = QLabel(
            "Son standard (grave) : ne rien faire\n"
            "Son deviant  (aigu)  : appuyer\n\n"
            "D1: 80/20 standard   D2: 80/20 dense\n"
            "D3: 80/20 court      D4: 70/30"
        )
        info.setStyleSheet("color: #808080; font-size: 11px; padding: 4px;")
        lo.addWidget(info)

        grp, self.sp = _make_training_group(30, self._train)
        lo.addWidget(grp)
        lo.addStretch()

    def _run(self, did):
        self.menu.run_experiment({'task_name': self.TASK, 'design_id': did})

    def _train(self):
        n = self.sp.value()
        self.menu.run_experiment({
            'task_name': self.TASK, 'design_id': 3,
            'extra_params': {
                'block_sequence': [{'n_trials': n}],
                'rest_duration': 5.0,
            },
        })

# ═════════════════════════════════════════════════════════════════════
# Motor SCAN
# ═════════════════════════════════════════════════════════════════════

from PyQt6.QtCore import QTimer, Qt
import time as _time


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
        MotorPanel._pending_chrono = None  # single run, no chrono after
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': 1,
        })

    def _run_combined(self, run_num):
        if run_num < 3:
            MotorPanel._pending_chrono = 120  # 2min between runs
        else:
            MotorPanel._pending_chrono = None
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': run_num + 1,  # designs 2, 3, 4
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