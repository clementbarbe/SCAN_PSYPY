"""
Task package — lazy registration.
Only register tasks that actually exist.
"""

from tasks.registry import register_lazy, get_task, list_tasks

register_lazy('motor', 'tasks.motor', 'MotorTask')

__all__ = ['get_task', 'list_tasks']