"""
Subject / session management utilities.
"""

from __future__ import annotations

from pathlib import Path
from config.settings import ExperimentSettings


def ensure_directories(settings: ExperimentSettings, task_name: str) -> Path:
    task_dir = settings.task_dir(task_name)
    task_dir.mkdir(parents=True, exist_ok=True)
    settings.log_dir().mkdir(parents=True, exist_ok=True)
    return task_dir


def check_existing_data(settings: ExperimentSettings, task_name: str) -> list[Path]:
    task_dir = settings.task_dir(task_name)
    if not task_dir.exists():
        return []
    return sorted(task_dir.glob('*.csv'))


def next_run_number(settings: ExperimentSettings, task_name: str) -> str:
    """
    Determine next run number based on existing CSV files.

    Scans for files matching sub-XX_ses-XX_task-XX_run-XX_*.csv
    and returns the next available run number.
    """
    task_dir = settings.task_dir(task_name)
    if not task_dir.exists():
        return '01'

    prefix = (
        f"sub-{settings.participant_id}_ses-{settings.session}"
        f"_task-{task_name}_run-"
    )

    existing_runs = set()
    for f in task_dir.glob('*.csv'):
        name = f.stem
        if prefix in name:
            # Extract run number
            try:
                after_run = name.split('_run-')[1]
                run_str = after_run.split('_')[0]
                existing_runs.add(int(run_str))
            except (IndexError, ValueError):
                pass

    if not existing_runs:
        return '01'

    return f"{max(existing_runs) + 1:02d}"