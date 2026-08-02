"""
WhatsApp Web MCP Server
Model Context Protocol server for WhatsApp Web automation
"""
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# MCP Server implementation
class WhatsAppWebMCPServer:
    """MCP Server for WhatsApp Web automation"""
    
    def __init__(self):
        self.name = "whatsapp-web"
        self.version = "1.0.0"
        self.description = "WhatsApp Web automation via browser"
        self.tools = []
        self.resources = []
        self._setup_tools()
        self._setup_resources()
    
    def _setup_tools(self):
        """Define MCP tools"""
        self.tools = [
            {
                "name": "whatsapp_send_message",
                "description": "Send a text message to a phone number via WhatsApp Web",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "Phone number with country code (e.g., +201018541802)"
                        },
                        "message": {
                            "type": "string",
                            "description": "Message text to send"
                        }
                    },
                    "required": ["phone", "message"]
                }
            },
            {
                "name": "whatsapp_send_image",
                "description": "Send an image with optional caption",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "phone": {
                            "type": "string",
                            "description": "Phone number with country code"
                        },
                        "image_path": {
                            "type": "string",
                            "description": "Path to image file"
                        },
                        "caption": {
                            "type": "string",
                            "description": "Optional caption for the image"
                        }
                    },
                    "required": ["phone", "image_path"]
                }
            },
            {
                "name": "whatsapp_get_unread",
                "description": "Get all unread messages from WhatsApp Web",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "whatsapp_get_chats",
                "description": "Get list of recent chats",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of chats to retrieve",
                            "default": 20
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "whatsapp_search_contact",
                "description": "Search for a contact by name or phone number",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (name or phone number)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "whatsapp_start",
                "description": "Start WhatsApp Web automation and authenticate",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "headless": {
                            "type": "boolean",
                            "description": "Run browser in headless mode",
                            "default": False
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "whatsapp_stop",
                "description": "Stop WhatsApp Web automation",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "whatsapp_status",
                "description": "Check WhatsApp Web connection status",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "whatsapp_screenshot",
                "description": "Take a screenshot of WhatsApp Web",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Screenshot filename",
                            "default": "whatsapp_screenshot.png"
                        }
                    },
                    "required": []
                }
            }
        ]
    
    def _setup_resources(self):
        """Define MCP resources"""
        self.resources = [
            {
                "uri": "whatsapp://status",
                "name": "WhatsApp Status",
                "description": "Current WhatsApp Web connection status",
                "mimeType": "application/json"
            },
            {
                "uri": "whatsapp://chats",
                "name": "WhatsApp Chats",
                "description": "List of recent WhatsApp chats",
                "mimeType": "application/json"
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Handle MCP tool calls"""
        from src.services.whatsapp_web import get_whatsapp_web
        
        whatsapp = await get_whatsapp_web()
        
        try:
            if tool_name == "whatsapp_send_message":
                success = await whatsapp.send_message(
                    phone=arguments["phone"],
                    message=arguments["message"]
                )
                return {
                    "success": success,
                    "message": f"Message sent to {arguments['phone']}" if success else "Failed to send message"
                }
            
            elif tool_name == "whatsapp_send_image":
                success = await whatsapp.send_image(
                    phone=arguments["phone"],
                    image_path=arguments["image_path"],
                    caption=arguments.get("caption", "")
                )
                return {
                    "success": success,
                    "message": f"Image sent to {arguments['phone']}" if success else "Failed to send image"
                }
            
            elif tool_name == "whatsapp_get_unread":
                messages = await whatsapp.get_unread_messages()
                return {
                    "success": True,
                    "messages": messages,
                    "count": len(messages)
                }
            
            elif tool_name == "whatsapp_get_chats":
                limit = arguments.get("limit", 20)
                chats = await whatsapp.get_chat_list()
                return {
                    "success": True,
                    "chats": chats[:limit],
                    "count": len(chats[:limit])
                }
            
            elif tool_name == "whatsapp_search_contact":
                results = await whatsapp.search_contact(arguments["query"])
                return {
                    "success": True,
                    "results": results,
                    "count": len(results)
                }
            
            elif tool_name == "whatsapp_start":
                headless = arguments.get("headless", False)
                whatsapp.headless = headless
                success = await whatsapp.start()
                return {
                    "success": success,
                    "message": "WhatsApp Web started" if success else "Failed to start WhatsApp Web",
                    "authenticated": whatsapp.is_authenticated
                }
            
            elif tool_name == "whatsapp_stop":
                await whatsapp.stop()
                return {
                    "success": True,
                    "message": "WhatsApp Web stopped"
                }
            
            elif tool_name == "whatsapp_status":
                is_online = await whatsapp.is_online()
                return {
                    "success": True,
                    "is_running": whatsapp.is_running,
                    "is_authenticated": whatsapp.is_authenticated,
                    "is_online": is_online
                }
            
            elif tool_name == "whatsapp_screenshot":
                filename = arguments.get("filename", "whatsapp_screenshot.png")
                filepath = await whatsapp.take_screenshot(filename)
                return {
                    "success": bool(filepath),
                    "filepath": filepath,
                    "message": f"Screenshot saved to {filepath}" if filepath else "Failed to take screenshot"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown tool: {tool_name}"
                }
                
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def handle_resource_read(self, uri: str) -> dict[str, Any]:
        """Handle MCP resource reads"""
        from src.services.whatsapp_web import get_whatsapp_web
        
        whatsapp = await get_whatsapp_web()
        
        if uri == "whatsapp://status":
            is_online = await whatsapp.is_online()
            return {
                "is_running": whatsapp.is_running,
                "is_authenticated": whatsapp.is_authenticated,
                "is_online": is_online,
                "timestamp": datetime.now().isoformat()
            }
        
        elif uri == "whatsapp://chats":
            chats = await whatsapp.get_chat_list()
            return {
                "chats": chats,
                "count": len(chats),
                "timestamp": datetime.now().isoformat()
            }
        
        else:
            raise ValueError(f"Unknown resource URI: {uri}")
    
    def get_tools_schema(self) -> list[dict[str, Any]]:
        """Get MCP tools schema"""
        return [
            {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": tool["inputSchema"]
            }
            for tool in self.tools
        ]
    
    def get_resources_schema(self) -> list[dict[str, Any]]:
        """Get MCP resources schema"""
        return self.resources


# Global MCP server instance
mcp_server = WhatsAppWebMCPServer()


def get_mcp_server() -> WhatsAppWebMCPServer:
    """Get MCP server instance"""
    return mcp_server
