"""
WebSocket Routes — مسارات الويب سوكت
=====================================
WebSocket endpoint for CityEstate Bridge Chrome Extension.

Protocol:
- Extension connects: ws://localhost:8000/ws/bridge?token=<jwt>&profile_id=<id>
- Bidirectional JSON messages
- Automatic reconnection support
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect

from src.api.deps import require_auth
from src.api.websocket_manager import ws_manager

logger = logging.getLogger("cityestate.routes.websocket")

router = APIRouter()


# ---------------------------------------------------------------------------
# WebSocket Authentication Helper
# ---------------------------------------------------------------------------
def _verify_ws_token(token: str) -> dict | None:
    """Verify JWT token for WebSocket connection.

    Returns payload dict if valid, None if invalid.
    """
    try:
        from src.api.auth import decode_jwt_token
        payload = decode_jwt_token(token)
        return payload
    except Exception as e:
        logger.warning("WebSocket auth failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Message Processing Helper
# ---------------------------------------------------------------------------
async def _handle_bridge_message(data: dict, profile_id: str) -> dict | None:
    """Process a message from the Extension and return a response.

    Returns:
        Response dict to send back, or None for no response.
    """
    msg_type = data.get("type", "")

    if msg_type == "AUTH":
        logger.info("Auth confirmed: profile=%s", profile_id)
        return {"type": "AUTH_OK", "timestamp": datetime.now(timezone.utc).isoformat()}

    if msg_type == "HEARTBEAT":
        ws_manager.update_heartbeat(profile_id)
        return {"type": "HEARTBEAT_ACK", "timestamp": datetime.now(timezone.utc).isoformat()}

    if msg_type == "WHATSAPP_MESSAGE":
        return await _handle_whatsapp_message(data, profile_id)

    if msg_type == "WHATSAPP_READY":
        logger.info("WhatsApp chat ready: profile=%s, chat=%s", profile_id, data.get("chatId"))
        return None

    if msg_type == "FACEBOOK_POST":
        return await _handle_facebook_post(data, profile_id)

    if msg_type == "TYPING_COMPLETE":
        logger.info("Typing complete: profile=%s, chat=%s", profile_id, data.get("chatId"))
        return None

    if msg_type == "FLEET_STATUS":
        return {
            "type": "FLEET_STATUS_RESPONSE",
            "profiles": ws_manager.get_connected_profiles(),
        }

    logger.warning("Unknown message type: %s", msg_type)
    return None


async def _handle_whatsapp_message(data: dict, profile_id: str) -> dict | None:
    """Process incoming WhatsApp message from Extension."""
    payload = data.get("payload", {})
    chat_id = payload.get("chatId", "")
    sender_name = payload.get("senderName", "عميل")
    message_text = payload.get("text", "")

    if not message_text:
        return None

    logger.info(
        "WhatsApp message: profile=%s, sender=%s, length=%d",
        profile_id, sender_name, len(message_text)
    )

    try:
        from src.api.bridge_handler import process_incoming_message
        from src.api.deps import SessionLocal

        db = SessionLocal()
        try:
            result = await process_incoming_message(
                profile_id=profile_id,
                chat_id=chat_id,
                sender_name=sender_name,
                message_text=message_text,
                platform="whatsapp",
                db_session=db,
            )

            # Build response
            response = {
                "type": "LEAD_SCORE",
                "payload": {
                    "chatId": chat_id,
                    "leadScore": result["lead_score"],
                    "intent": result["intent"],
                    "matchedProperties": result["matched_properties"],
                },
            }

            # If needs handoff, notify user
            if result["needs_handoff"]:
                response["payload"]["handoff"] = {
                    "reason": "hot_lead",
                    "senderName": sender_name,
                    "chatId": chat_id,
                }

            # If AI generated a response, send it to type
            if result["response"]:
                await ws_manager.send_to_profile(profile_id, {
                    "type": "SEND_WHATSAPP",
                    "payload": {
                        "chatId": chat_id,
                        "text": result["response"],
                    },
                })

            return response

        finally:
            db.close()

    except Exception as e:
        logger.error("Failed to process WhatsApp message: %s", e)
        return {
            "type": "ERROR",
            "payload": {"message": "Failed to process message"},
        }


async def _handle_facebook_post(data: dict, profile_id: str) -> dict | None:
    """Process incoming Facebook post from Extension."""
    payload = data.get("payload", {})
    group_id = payload.get("groupId", "")
    group_name = payload.get("groupName", "")
    payload.get("postId", "")
    post_url = payload.get("postUrl", "")
    author_name = payload.get("authorName", "")
    post_text = payload.get("text", "")

    if not post_text:
        return None

    logger.info(
        "Facebook post: profile=%s, group=%s, author=%s",
        profile_id, group_name, author_name
    )

    try:
        from src.api.bridge_handler import parse_intent, score_lead

        # Parse intent from the post
        intent = parse_intent(post_text)

        # Only process buyer-intent posts
        if not intent or intent.get("status") == "rejected":
            return None

        # Score the lead
        lead_score = score_lead(intent, post_text)

        # Save to database
        from src.api.deps import SessionLocal
        from src.database.ingester import Lead

        db = SessionLocal()
        try:
            title = author_name or post_text[:80]
            lead = Lead(
                source="facebook_bridge",
                title=title,
                url=f"facebook:{post_url or 'unknown'}",
                lead_type="Buyer",
                interest=post_text[:500],
                score=lead_score.get("score", 0),
                tags=f"profile:{profile_id},group:{group_id}",
            )
            db.add(lead)
            db.commit()

            return {
                "type": "FACEBOOK_LEAD_CAPTURED",
                "payload": {
                    "leadId": lead.id,
                    "authorName": author_name,
                    "groupName": group_name,
                    "leadScore": lead_score,
                    "intent": intent,
                },
            }
        finally:
            db.close()

    except Exception as e:
        logger.error("Failed to process Facebook post: %s", e)
        return None


# ---------------------------------------------------------------------------
# WebSocket Endpoint
# ---------------------------------------------------------------------------
@router.websocket("/ws/bridge")
async def bridge_websocket(
    websocket: WebSocket,
    token: str = Query(default=""),
    profile_id: str = Query(default=""),
):
    """
    WebSocket endpoint for CityEstate Bridge Chrome Extension.

    Connection URL: ws://localhost:8000/ws/bridge?token=<jwt>&profile_id=<id>

    Message Protocol (Extension → Backend):
        - WHATSAPP_MESSAGE: Incoming WhatsApp message
        - WHATSAPP_READY: Chat opened in browser
        - FACEBOOK_POST: New Facebook post found
        - TYPING_COMPLETE: Extension finished typing
        - HEARTBEAT: Keep-alive signal
        - FLEET_STATUS: Request fleet status

    Message Protocol (Backend → Extension):
        - SEND_WHATSAPP: Type and send this message
        - LEAD_SCORE: Lead scoring result
        - MATCHED_PROPERTIES: Top matched properties
        - AGENT_HANDOFF: Human intervention needed
        - CONTENT_TO_POST: Post content to Facebook Group
    """
    # Validate parameters
    if not profile_id:
        await websocket.close(code=4000, reason="profile_id required")
        return

    # Verify JWT token
    if not token:
        await websocket.close(code=4001, reason="token required")
        return
    payload = _verify_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="invalid token")
        return

    # Accept and register connection
    user_agent = websocket.headers.get("user-agent", "")
    await ws_manager.connect(websocket, profile_id, user_agent)

    try:
        while True:
            # Receive message from Extension
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Invalid JSON from profile %s", profile_id)
                continue

            # Process and get response
            response = await _handle_bridge_message(data, profile_id)
            if response:
                await ws_manager.send_to_profile(profile_id, response)

    except WebSocketDisconnect:
        await ws_manager.disconnect(profile_id)
        logger.info("Extension disconnected: profile=%s", profile_id)

    except Exception as e:
        logger.error("WebSocket error for profile %s: %s", profile_id, e)
        await ws_manager.disconnect(profile_id)


# ---------------------------------------------------------------------------
# REST Endpoints for Fleet Monitoring (used by Dashboard)
# ---------------------------------------------------------------------------
@router.get("/bridge/status")
def bridge_status(user: dict = Depends(require_auth)) -> dict:
    """Get WebSocket connection status for all fleet members."""
    try:
        return {
            "status": "ok",
            "connections": ws_manager.get_connected_profiles(),
            "stats": ws_manager.get_stats(),
        }
    except Exception as e:
        logger.error("Failed to get bridge status: %s", e)
        return {"status": "error", "error": str(e)}


@router.get("/bridge/messages")
def bridge_messages(user: dict = Depends(require_auth), limit: int = 50) -> dict:
    """Get recent bridge messages (from all connected profiles)."""
    try:
        return {
            "status": "ok",
            "messages": [],
            "note": "Messages are logged in message_log table",
        }
    except Exception as e:
        logger.error("Failed to get bridge messages: %s", e)
        return {"status": "error", "error": str(e)}
