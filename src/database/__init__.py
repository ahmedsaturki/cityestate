"""
Database Module
===============
CSV ingestion, validation, deduplication, and CRM sync preparation.
"""

from .ingester import CSVIngester

__all__ = ["CSVIngester"]
