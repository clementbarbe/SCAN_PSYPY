#!/usr/bin/env python3
"""
fMRI Experiment Framework — entry point.

Loop: menu -> experiment -> menu -> experiment -> ...
GUI state (name, session, screen, mode) persists between runs.
Chrono in SCAN tab keeps running between reopens.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.console import init_console
init_console()


def main():
    from gui.launcher import show_menu
    from core.experiment import Experiment

    gui_state = None

    while True:
        config = show_menu(last_state=gui_state)
        if config is None:
            print("Ferme sans lancer d'experience.")
            break

        # Save GUI state for next reopen
        gui_state = config.get('_gui_state', None)

        settings = config['settings']
        task_name = config['task_name']
        design_id = config['design_id']
        extra = config.get('extra_params', {})

        exp = Experiment(settings)
        try:
            saved = exp.run_task(task_name, design_id=design_id, **extra)
            if saved:
                print(f"\n[OK] Data saved: {saved}")
        finally:
            exp.cleanup()


if __name__ == '__main__':
    main()