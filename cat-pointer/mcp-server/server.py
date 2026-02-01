"""
Cat Pointer MCP Server

Provides 3 tools for pointing at objects:
- point_carrot: Point at the carrot
- point_tissue: Point at the tissue
- point_mickey: Point at Mickey Mouse
"""

import asyncio

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

NEXT_APP_URL = "http://localhost:3000"

server = Server("cat-pointer")


async def send_point_command(target: str) -> str:
    """Send point command to Next.js app"""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{NEXT_APP_URL}/api/point",
                json={"target": target},
                timeout=5.0,
            )
            if response.status_code == 200:
                return f"喵~ 小猫正在指向{target}！"
            else:
                return f"指向失败: {response.text}"
        except httpx.ConnectError:
            return "无法连接到动画服务器，请确保 Next.js 应用正在运行"
        except Exception as e:
            return f"发生错误: {str(e)}"


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="point_carrot",
            description="让小猫指向萝卜🥕。当用户说'萝卜'、'胡萝卜'、'carrot'时调用此工具。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="point_tissue",
            description="让小猫指向纸巾🧻。当用户说'纸巾'、'纸'、'tissue'时调用此工具。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
        Tool(
            name="point_mickey",
            description="让小猫指向米奇🐭。当用户说'米奇'、'米老鼠'、'Mickey'时调用此工具。",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls"""
    target_map = {
        "point_carrot": "萝卜",
        "point_tissue": "纸巾",
        "point_mickey": "米奇",
    }

    if name not in target_map:
        return [TextContent(type="text", text=f"未知工具: {name}")]

    target = target_map[name]
    result = await send_point_command(target)
    return [TextContent(type="text", text=result)]


async def run_server():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    """Entry point"""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
