"""
Tests for the messaging module (src/messaging/).
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from src.messaging import MessageDispatcher


class TestMessageDispatcher:
    """Test the MessageDispatcher class."""

    def test_dispatcher_init(self):
        """Test that MessageDispatcher initializes with a db session."""
        mock_db = MagicMock()
        dispatcher = MessageDispatcher(mock_db)
        assert dispatcher.db is mock_db

    def test_send_match_notification_success(self):
        """Test successful match notification dispatch."""
        mock_db = MagicMock()
        dispatcher = MessageDispatcher(mock_db)

        mock_request = MagicMock()
        mock_request.id = 1
        mock_request.client_name = "Test Client"
        mock_request.area = "New Cairo"
        mock_request.budget_min = "500000"

        result = dispatcher.send_match_notification(mock_request)

        assert result["status"] == "sent"
        assert result["request_id"] == 1
        assert result["channel"] == "whatsapp"
        assert "Hello Test Client" in result["message"]

    def test_send_match_notification_failure(self):
        """Test failed match notification dispatch."""
        mock_db = MagicMock()
        mock_db.commit.side_effect = [Exception("DB error"), None]
        dispatcher = MessageDispatcher(mock_db)

        mock_request = MagicMock()
        mock_request.id = 1
        mock_request.client_name = "Test Client"

        result = dispatcher.send_match_notification(mock_request)

        assert result["status"] == "failed"
        assert result["request_id"] == 1

    def test_send_campaign_message_success(self):
        """Test successful campaign message dispatch."""
        mock_db = MagicMock()
        dispatcher = MessageDispatcher(mock_db)

        mock_request = MagicMock()
        mock_request.id = 1
        mock_request.client_name = "Test Client"

        result = dispatcher.send_campaign_message(
            mock_request,
            message="Test campaign message",
            channel="whatsapp",
        )

        assert result["status"] == "sent"
        assert result["channel"] == "whatsapp"

    def test_send_bulk_notifications(self):
        """Test bulk notification dispatch."""
        mock_db = MagicMock()
        dispatcher = MessageDispatcher(mock_db)

        mock_requests = []
        for i in range(3):
            req = MagicMock()
            req.id = i
            req.client_name = f"Client {i}"
            req.area = "New Cairo"
            req.budget_min = "500000"
            mock_requests.append(req)

        result = dispatcher.send_bulk_notifications(mock_requests)

        assert result["total"] == 3
        assert result["status"] == "complete"

    def test_build_match_message(self):
        """Test match message building."""
        mock_db = MagicMock()
        dispatcher = MessageDispatcher(mock_db)

        mock_request = MagicMock()
        mock_request.client_name = "Ahmed"
        mock_request.area = "New Cairo"
        mock_request.budget_min = "500000"

        message = dispatcher._build_match_message(mock_request)

        assert "Ahmed" in message
        assert "New Cairo" in message
        assert "500000" in message
        assert "CityEstate Team" in message