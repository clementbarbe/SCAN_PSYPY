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

from PyQt6.QtCore import QTimer, QElapsedTimer


@register_panel('SCAN')
class MotorPanel(QWidget):
    TASK = 'motor'

    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        self._chrono_timer = QTimer(self)
        self._chrono_timer.setInterval(100)
        self._chrono_timer.timeout.connect(self._update_chrono)
        self._elapsed = QElapsedTimer()
        self._target_rest = 0
        self._last_task_type = 0
        self._build()

    def _build(self):
        lo = QVBoxLayout(self)
        lo.setSpacing(10)

        # ── Task 1 ───────────────────────────────────────────────────
        t1_group = QGroupBox("Tache 1 — 3 conditions (RH/LH/RF)")
        t1 = QGridLayout(t1_group)
        t1.setSpacing(6)

        info1 = QLabel("12 essais/run | 202s | repos inter-run: 1min30")
        info1.setStyleSheet("color: #808080; font-size: 11px;")
        t1.addWidget(info1, 0, 0, 1, 3)

        for i in range(3):
            btn = QPushButton(f"Run {i+1}")
            btn.setObjectName("run")
            btn.setToolTip(f"Task 1 Run {i+1} — 3min22")
            btn.clicked.connect(lambda _, r=i+1: self._run_task1(r))
            t1.addWidget(btn, 1, i)

        lo.addWidget(t1_group)

        # ── Task 2 ───────────────────────────────────────────────────
        t2_group = QGroupBox("Tache 2 — 6 conditions (simples + combinees)")
        t2 = QGridLayout(t2_group)
        t2.setSpacing(6)

        info2 = QLabel("32 essais/run | 630s | repos inter-run: 2min")
        info2.setStyleSheet("color: #808080; font-size: 11px;")
        t2.addWidget(info2, 0, 0, 1, 3)

        for i in range(3):
            btn = QPushButton(f"Run {i+1}")
            btn.setObjectName("run")
            btn.setToolTip(f"Task 2 Run {i+1} — 10min30")
            btn.clicked.connect(lambda _, r=i+1: self._run_task2(r))
            t2.addWidget(btn, 1, i)

        lo.addWidget(t2_group)

        # ── Chronometre ──────────────────────────────────────────────
        chrono_group = QGroupBox("Chronometre repos inter-run")
        cl = QVBoxLayout(chrono_group)

        self._chrono_label = QLabel("--:--")
        self._chrono_label.setStyleSheet(
            "font-size: 28px; font-weight: bold; "
            "font-family: monospace; padding: 8px;"
        )
        self._chrono_label.setAlignment(
            __import__('PyQt6.QtCore', fromlist=['Qt']).Qt.AlignmentFlag.AlignCenter
        )
        cl.addWidget(self._chrono_label)

        self._chrono_status = QLabel("")
        self._chrono_status.setStyleSheet(
            "color: #808080; font-size: 11px; padding: 2px;"
        )
        self._chrono_status.setAlignment(
            __import__('PyQt6.QtCore', fromlist=['Qt']).Qt.AlignmentFlag.AlignCenter
        )
        cl.addWidget(self._chrono_status)

        lo.addWidget(chrono_group)
        lo.addStretch()

    def _run_task1(self, run_num):
        design_id = run_num  # designs 1, 2, 3
        self._last_task_type = 1
        self._target_rest = 90
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': design_id,
        })
        # Start chrono after experiment returns
        self._start_chrono()

    def _run_task2(self, run_num):
        design_id = run_num + 3  # designs 4, 5, 6
        self._last_task_type = 2
        self._target_rest = 120
        self.menu.run_experiment({
            'task_name': self.TASK,
            'design_id': design_id,
        })
        self._start_chrono()

    def _start_chrono(self):
        """Start rest countdown after a run ends."""
        self._elapsed.start()
        self._chrono_timer.start()
        task_label = f"Tache {self._last_task_type}"
        target_str = f"{self._target_rest // 60}min{self._target_rest % 60:02d}s"
        self._chrono_status.setText(
            f"{task_label} termine — repos recommande: {target_str}"
        )
        self._chrono_status.setStyleSheet(
            "color: #e08000; font-size: 11px; padding: 2px;"
        )

    def _update_chrono(self):
        """Update chrono display every 100ms."""
        elapsed_ms = self._elapsed.elapsed()
        elapsed_s = elapsed_ms / 1000.0
        mins = int(elapsed_s) // 60
        secs = int(elapsed_s) % 60
        tenths = int((elapsed_s % 1) * 10)

        self._chrono_label.setText(f"{mins:02d}:{secs:02d}.{tenths}")

        if elapsed_s >= self._target_rest:
            self._chrono_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; "
                "font-family: monospace; padding: 8px; "
                "color: #00a000;"
            )
            self._chrono_status.setText("Repos termine — pret pour le run suivant")
            self._chrono_status.setStyleSheet(
                "color: #00a000; font-size: 11px; padding: 2px;"
            )
        else:
            remaining = self._target_rest - elapsed_s
            r_mins = int(remaining) // 60
            r_secs = int(remaining) % 60
            self._chrono_label.setStyleSheet(
                "font-size: 28px; font-weight: bold; "
                "font-family: monospace; padding: 8px; "
                "color: #e0e0e0;"
            )
            self._chrono_status.setText(
                f"Reste: {r_mins:02d}:{r_secs:02d}"
            )