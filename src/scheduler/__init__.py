"""
Scheduler Module — CityEstate Auto-Run Engine
=============================================
APScheduler-based background job scheduler for automated tasks:
- Match-making runs
- WhatsApp notifications
- Data backups
- Session vault checks
"""

from src.scheduler.engine import SchedulerEngine

__all__ = ["SchedulerEngine"]
