"""
WhatsApp Web Skill for CityEstate Agent
Browser-based WhatsApp automation
"""
import asyncio
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class WhatsAppWebSkill:
    """WhatsApp Web automation skill for CityEstate agent"""
    
    name = "whatsapp_web"
    description = "Automate WhatsApp Web via browser for sending/receiving messages"
    
    def __init__(self):
        self.mcp_server = None
    
    async def _get_mcp_server(self):
        """Get MCP server instance"""
        if self.mcp_server is None:
            from src.mcp.whatsapp_web_server import get_mcp_server
            self.mcp_server = get_mcp_server()
        return self.mcp_server
    
    async def send_message(self, phone: str, message: str) -> dict[str, Any]:
        """Send a text message"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_send_message", {
            "phone": phone,
            "message": message
        })
    
    async def send_image(self, phone: str, image_path: str, caption: str = "") -> dict[str, Any]:
        """Send an image with caption"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_send_image", {
            "phone": phone,
            "image_path": image_path,
            "caption": caption
        })
    
    async def get_unread_messages(self) -> dict[str, Any]:
        """Get all unread messages"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_get_unread", {})
    
    async def get_chats(self, limit: int = 20) -> dict[str, Any]:
        """Get list of recent chats"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_get_chats", {"limit": limit})
    
    async def search_contact(self, query: str) -> dict[str, Any]:
        """Search for a contact"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_search_contact", {"query": query})
    
    async def start(self, headless: bool = False) -> dict[str, Any]:
        """Start WhatsApp Web"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_start", {"headless": headless})
    
    async def stop(self) -> dict[str, Any]:
        """Stop WhatsApp Web"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_stop", {})
    
    async def status(self) -> dict[str, Any]:
        """Check connection status"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_status", {})
    
    async def screenshot(self, filename: str = "whatsapp_screenshot.png") -> dict[str, Any]:
        """Take a screenshot"""
        server = await self._get_mcp_server()
        return await server.handle_tool_call("whatsapp_screenshot", {"filename": filename})
    
    def get_tools(self) -> list[dict[str, Any]]:
        """Get available tools for CrewAI"""
        return [
            {
                "name": "send_whatsapp_message",
                "description": "Send a WhatsApp message to a phone number using browser automation",
                "function": self._send_message_tool
            },
            {
                "name": "get_whatsapp_unread",
                "description": "Get all unread WhatsApp messages",
                "function": self._get_unread_tool
            },
            {
                "name": "get_whatsapp_chats",
                "description": "Get list of recent WhatsApp chats",
                "function": self._get_chats_tool
            },
            {
                "name": "search_whatsapp_contact",
                "description": "Search for a WhatsApp contact",
                "function": self._search_contact_tool
            },
            {
                "name": "whatsapp_status",
                "description": "Check WhatsApp Web connection status",
                "function": self._status_tool
            }
        ]
    
    async def _send_message_tool(self, phone: str, message: str) -> str:
        """Tool for sending messages"""
        result = await self.send_message(phone, message)
        return json.dumps(result, ensure_ascii=False)
    
    async def _get_unread_tool(self) -> str:
        """Tool for getting unread messages"""
        result = await self.get_unread_messages()
        return json.dumps(result, ensure_ascii=False)
    
    async def _get_chats_tool(self, limit: int = 20) -> str:
        """Tool for getting chat list"""
        result = await self.get_chats(limit)
        return json.dumps(result, ensure_ascii=False)
    
    async def _search_contact_tool(self, query: str) -> str:
        """Tool for searching contacts"""
        result = await self.search_contact(query)
        return json.dumps(result, ensure_ascii=False)
    
    async def _status_tool(self) -> str:
        """Tool for checking status"""
        result = await self.status()
        return json.dumps(result, ensure_ascii=False)


# CrewAI Tool definitions
def send_whatsapp_message(phone: str, message: str) -> str:
    """Send a WhatsApp message using browser automation"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.send_message(phone, message))
    return json.dumps(result, ensure_ascii=False)


def get_whatsapp_unread() -> str:
    """Get all unread WhatsApp messages"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.get_unread_messages())
    return json.dumps(result, ensure_ascii=False)


def get_whatsapp_chats(limit: int = 20) -> str:
    """Get list of recent WhatsApp chats"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.get_chats(limit))
    return json.dumps(result, ensure_ascii=False)


def search_whatsapp_contact(query: str) -> str:
    """Search for a WhatsApp contact"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.search_contact(query))
    return json.dumps(result, ensure_ascii=False)


def get_whatsapp_status() -> str:
    """Check WhatsApp Web connection status"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.status())
    return json.dumps(result, ensure_ascii=False)


def start_whatsapp_web(headless: bool = False) -> str:
    """Start WhatsApp Web automation"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.start(headless))
    return json.dumps(result, ensure_ascii=False)


def stop_whatsapp_web() -> str:
    """Stop WhatsApp Web automation"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.stop())
    return json.dumps(result, ensure_ascii=False)


def take_whatsapp_screenshot(filename: str = "whatsapp_screenshot.png") -> str:
    """Take a screenshot of WhatsApp Web"""
    skill = WhatsAppWebSkill()
    result = asyncio.run(skill.screenshot(filename))
    return json.dumps(result, ensure_ascii=False)


def get_whatsapp_web_tools():
    """Get all WhatsApp Web tools for CrewAI"""
    return [
        {
            "name": "send_whatsapp_web_message",
            "description": "Send a WhatsApp message using browser automation",
            "function": send_whatsapp_message
        },
        {
            "name": "get_whatsapp_web_unread",
            "description": "Get all unread WhatsApp messages",
            "function": get_whatsapp_unread
        },
        {
            "name": "get_whatsapp_web_chats",
            "description": "Get list of recent WhatsApp chats",
            "function": get_whatsapp_chats
        },
        {
            "name": "search_whatsapp_web_contact",
            "description": "Search for a WhatsApp contact",
            "function": search_whatsapp_contact
        },
        {
            "name": "get_whatsapp_web_status",
            "description": "Check WhatsApp Web connection status",
            "function": get_whatsapp_status
        }
    ]
