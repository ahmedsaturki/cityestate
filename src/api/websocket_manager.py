"""
WebSocket Manager — مدير اتصالات الويب سوكت
============================================
Manages WebSocket connections between the Chrome Extension (Bridge)
and the CityEstate AI Brain.

Supports:
- Multiple simultaneous Extension connections (Fleet)
- Profile-based routing (each Chrome Profile is a separate fleet member)
- Message queuing for offline profiles
- Heartbeat-based connection health monitoring
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fastapi import WebSocket

logger = logging.getLogger("cityestate.websocket")


@dataclass
class ConnectionInfo:
    """Tracks a single WebSocket connection from a Chrome Extension."""
    ws: WebSocket
    profile_id: str
    user_agent: str = ""
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    messages_sent: int = 0
    messages_received: int = 0
    is_active: bool = True


class WebSocketManager:
    """
    Manages all WebSocket connections from CityEstate Bridge Extensions.

    Architecture:
    - Each Chrome Profile connects with a unique profile_id
    - Messages are routed to the correct profile
    - Offline messages are queued and delivered on reconnect
    """

    def __init__(self):
        self._connections: dict[str, ConnectionInfo] = {}
        self._message_queue: dict[str, list[dict]] = {}
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------
    async def connect(self, websocket: WebSocket, profile_id: str, user_agent: str = ""):
        """Accept and register a new Extension connection."""
        await websocket.accept()

        # Close existing connection for this profile if any
        if profile_id in self._connections:
            old_conn = self._connections[profile_id]
            try:
                await old_conn.ws.close()
            except Exception as e:
                logger.debug("Failed to close old connection: %s", e)
            logger.info("Replaced existing connection for profile: %s", profile_id)

        self._connections[profile_id] = ConnectionInfo(
            ws=websocket,
            profile_id=profile_id,
            user_agent=user_agent,
        )

        logger.info(
            "Extension connected: profile=%s, total=%d",
            profile_id, len(self._connections)
        )

        # Deliver queued messages
        if profile_id in self._message_queue:
            queued = self._message_queue.pop(profile_id)
            for msg in queued:
                await self.send_to_profile(profile_id, msg)
            logger.info("Delivered %d queued messages to profile %s", len(queued), profile_id)

        # Start heartbeat checker if not running
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_checker())
            self._heartbeat_task.add_done_callback(
                lambda t: logger.error("Heartbeat checker failed: %s", t.exception()) if t.exception() else None
            )

    async def disconnect(self, profile_id: str):
        """Mark a profile as disconnected."""
        if profile_id in self._connections:
            conn = self._connections[profile_id]
            conn.is_active = False
            del self._connections[profile_id]
            logger.info(
                "Extension disconnected: profile=%s, remaining=%d",
                profile_id, len(self._connections)
            )

    def is_connected(self, profile_id: str) -> bool:
        """Check if a profile is currently connected."""
        return profile_id in self._connections and self._connections[profile_id].is_active

    def get_connected_profiles(self) -> list[dict]:
        """Return list of all connected profiles."""
        return [
            {
                "profile_id": conn.profile_id,
                "user_agent": conn.user_agent,
                "connected_at": conn.connected_at.isoformat(),
                "last_heartbeat": conn.last_heartbeat.isoformat(),
                "messages_sent": conn.messages_sent,
                "messages_received": conn.messages_received,
            }
            for conn in self._connections.values()
            if conn.is_active
        ]

    # ------------------------------------------------------------------
    # Message Sending
    # ------------------------------------------------------------------
    async def send_to_profile(self, profile_id: str, message: dict) -> bool:
        """Send a message to a specific Extension profile.

        Returns True if sent, False if queued (profile offline).
        """
        if profile_id not in self._connections:
            self._queue_message(profile_id, message)
            return False

        conn = self._connections[profile_id]
        if not conn.is_active:
            self._queue_message(profile_id, message)
            return False

        try:
            await conn.ws.send_json(message)
            conn.messages_sent += 1
            return True
        except Exception as e:
            logger.error("Failed to send to profile %s: %s", profile_id, e)
            conn.is_active = False
            del self._connections[profile_id]
            self._queue_message(profile_id, message)
            return False

    async def broadcast(self, message: dict) -> int:
        """Send a message to ALL connected profiles. Returns count sent."""
        sent = 0
        disconnected = []

        for profile_id, conn in self._connections.items():
            if not conn.is_active:
                disconnected.append(profile_id)
                continue
            try:
                await conn.ws.send_json(message)
                conn.messages_sent += 1
                sent += 1
            except Exception as e:
                logger.error("Broadcast failed for %s: %s", profile_id, e)
                disconnected.append(profile_id)

        for pid in disconnected:
            self._connections.pop(pid, None)

        return sent

    def _queue_message(self, profile_id: str, message: dict):
        """Queue a message for an offline profile."""
        if profile_id not in self._message_queue:
            self._message_queue[profile_id] = []

        # Keep max 100 queued messages per profile
        if len(self._message_queue[profile_id]) >= 100:
            self._message_queue[profile_id].pop(0)

        self._message_queue[profile_id].append(message)

    # ------------------------------------------------------------------
    # Heartbeat Monitoring
    # ------------------------------------------------------------------
    async def _heartbeat_checker(self):
        """Periodically check for stale connections AND send pings."""
        while True:
            await asyncio.sleep(self._heartbeat_interval)
            now = datetime.now(timezone.utc)
            stale = []

            for profile_id, conn in self._connections.items():
                elapsed = (now - conn.last_heartbeat).total_seconds()
                if elapsed > self._heartbeat_interval * 3:
                    stale.append(profile_id)
                else:
                    # Send ping to keep connection alive
                    try:
                        await conn.ws.send_json({"type": "PING", "ts": now.isoformat()})
                    except Exception:
                        stale.append(profile_id)

            for pid in stale:
                logger.warning("Stale connection removed: %s", pid)
                conn = self._connections.pop(pid, None)
                if conn:
                    try:
                        await conn.ws.close()
                    except Exception as e:
                        logger.debug("Failed to close stale connection: %s", e)

    def update_heartbeat(self, profile_id: str):
        """Update the heartbeat timestamp for a profile."""
        if profile_id in self._connections:
            self._connections[profile_id].last_heartbeat = datetime.now(timezone.utc)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------
    def get_stats(self) -> dict:
        """Return connection statistics."""
        total_sent = sum(c.messages_sent for c in self._connections.values())
        total_received = sum(c.messages_received for c in self._connections.values())
        return {
            "connected_profiles": len(self._connections),
            "queued_profiles": len(self._message_queue),
            "total_messages_sent": total_sent,
            "total_messages_received": total_received,
        }


# Singleton instance
ws_manager = WebSocketManager()
