import json
import json
import re
import asyncio
from typing import Optional, List, Dict
from contextlib import AsyncExitStack

from qq_bot.core.mcp_manager.mcp_model import mcp_model_dict
from qq_bot.utils.config import settings
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client


def format_tools_for_llm(tool) -> list:
    """对tool进行格式化
    Returns:
        格式化之后的tool描述
    """
    if "properties" in tool.inputSchema:
        name = tool.name
        function_description = tool.description
        required = []
        param_info_dict = {}
        for param_name, param_info in tool.inputSchema["properties"].items():
            required.append(param_name)
            param_info_dict[param_name] = param_info
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": function_description,
                    "parameters":{
                        "type": "object",
                        "properties": param_info_dict,
                        "required": required,

                    }
                }
            }
        ]
    return []



class McpRegister:
    def __init__(self, mcp_config_path: str):
        self._exit_stack: Optional[AsyncExitStack] = None
        self.sessions: List[ClientSession] = []
        self.tools: Dict[str, Dict] = {}
        self._lock = asyncio.Lock()
        self.is_connected = False
        self.tools_description: List[Dict] = []
        self._mcp_config_path = mcp_config_path

    # 工厂方法：异步创建并初始化
    @staticmethod
    async def create(mcp_config_path: str) -> "McpRegister":
        inst = McpRegister(mcp_config_path)
        await inst.async_init()
        return inst

    async def reconnect_session(self, session_index: int) -> bool:
        server_configs = load_server_configs(self._mcp_config_path)
        mcp_servers = list(server_configs["mcpServers"].items())

        if session_index >= len(mcp_servers):
            print(f"会话索引 {session_index} 超出范围")
            return False

        mcp_name, mcp_config = mcp_servers[session_index]
        url = mcp_config["url"]


        try:
            if session_index < len(self.sessions) and self.sessions[session_index]:
                sse_cm = sse_client(url)
                streams = await self._exit_stack.enter_async_context(sse_cm)
                session_cm = ClientSession(streams[0], streams[1])
                session = await self._exit_stack.enter_async_context(session_cm)
                await session.initialize()

                self.sessions[session_index] = session
                response = await session.list_tools()
                for tool in response.tools:
                    self.tools[tool.name] = {"tool": tool, "session_index": session_index}

                print(f"会话 {session_index} ({mcp_name}) 重连成功，获取 {len(response.tools)} 个工具")
                return True
            else:
                print(f"会话索引 {session_index} 超出范围")
                return False
        except Exception as e:
            print(f"重连会话 {session_index} 失败: {e}")
            return False



    async def execute_tool(self, tool_name: str, args: dict):
        # 在所有工具中查找
        if tool_name in self.tools:
            session_index = self.tools[tool_name]["session_index"]

            try:
                result = await self.sessions[session_index].call_tool(
                    tool_name, args
                )
                print(args)
                print(f"[提示]：正在调用工具 {tool_name} (来自服务器 {session_index + 1}): {result}")
                # if isinstance(result, dict) and "progress" in result:
                #     progress = result["progress"]
                #     total = result["total"]
                #     percentage = (progress / total) * 100
                #     print(f"Progress: {progress}/{total} ({percentage:.1f}%)")
                print(type(result.content),result.content)
                if tool_name in mcp_model_dict:
                    return f"{tool_name} Tool execution result: " + mcp_model_dict[tool_name](result.content)
                else:
                    return f"Tool execution result: "+"\n".join(cont.text for cont in result.content[:10])
            except Exception as e:
                error_msg = f"Error executing tool: {str(e)}"
                if await self.reconnect_session(session_index):
                    result = await self.sessions[session_index].call_tool(
                        tool_name, args
                    )
                    # return result.content[0].text
                    if tool_name in mcp_model_dict:
                        return f"{tool_name} Tool execution result: " + mcp_model_dict[tool_name](result.content)
                    else:
                        return f"Tool execution result: "+"\n".join(cont.text for cont in result.content[:10])
                else:
                    return error_msg
        else:
            return f"No tool found with name: {tool_name}"


    async def async_init(self) -> "McpRegister":
        await self.connect_servers(load_server_configs(self._mcp_config_path))
        return self

    async def connect_servers(self, server_configs: Dict):
        """连接多个 MCP 服务器"""
        async with self._lock:
            self._exit_stack = AsyncExitStack()
            for i, (mcp_name, mcp_config) in enumerate(server_configs["mcpServers"].items()):
                url = mcp_config["url"]
                print(f"尝试连接到服务器 {mcp_name}: {url}")
                try:
                    sse_cm = sse_client(url)
                    streams = await self._exit_stack.enter_async_context(sse_cm)
                    session_cm = ClientSession(streams[0], streams[1])
                    session = await self._exit_stack.enter_async_context(session_cm)
                    await session.initialize()
                    response = await session.list_tools()
                    for tool in response.tools:
                        self.tools[tool.name] = {"tool": tool, "session_index": i}
                    print(f"服务器 {mcp_name} 成功获取 {len(response.tools)} 个工具")
                    self.sessions.append(session)
                except Exception as e:
                    print(f"连接服务器 {mcp_name} 失败: {e}")
                    continue
            print(f"总共连接了 {len(self.sessions)} 个服务器，获取了 {len(self.tools)} 个工具")
            for info in self.tools.values():
                self.tools_description.extend(format_tools_for_llm(info["tool"]))
            print(self.tools_description)


    async def disconnect(self):
        """关闭所有会话"""
        async with self._lock:
            if self._exit_stack:
                await self._exit_stack.aclose()
            self.sessions.clear()
            self.tools.clear()


def load_server_configs(config_file: str) -> Dict:
    with open(config_file) as f:
        return json.load(f)


# ---------- 单例异步获取 ----------
mcp_register: Optional[McpRegister] = None


async def _init():
    global mcp_register
    if mcp_register is None:
        mcp_register = await McpRegister.create(settings.MCP_CONFIG_PATH)


async def get_mcp_register() -> McpRegister:
    """异步单例：第一次调用时初始化，后续直接返回已创建对象"""
    await _init()
    return mcp_register