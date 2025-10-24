import json
from openai.types.chat import ChatCompletionMessageToolCall

from qq_bot.core.agent.base import AgentBase
from qq_bot.core.tool_manager.base import ToolRegistrarBase
from qq_bot.core.tool_manager.tools.base import ToolBase
# from qq_bot.core import llm_registrar
from qq_bot.core.llm_manager.llm_registrar import get_llm_registrar
from qq_bot.utils.models import GroupMessageRecord
from qq_bot.utils.logging import logger
from qq_bot.utils.util import import_all_modules_from_package
import qq_bot.core.tool_manager.tools as bot_tools


class ToolRegistrar(ToolRegistrarBase):
    def __init__(self, agent: AgentBase):
        self.agent: AgentBase = agent
        self._load_tools()

    def _load_tools(self):
        import_all_modules_from_package(bot_tools)

        tools = ToolBase.__subclasses__()
        logger.info("正在注册Agent工具")

        self.tools: dict[str, ToolBase] = {tool.tool_name: tool for tool in tools}
        self.tool_dec: list[dict] = [tool.description for tool in tools]

        logger.info(f"已注册Agent工具: {', '.join(self.tools.keys())}")

    async def run(self, message: GroupMessageRecord) -> bool:
        llm_registrar = await get_llm_registrar()
        results: list[ChatCompletionMessageToolCall] | None = await llm_registrar.get(
            "bot_toolbox"
        ).run(message, tools=self.tool_dec)
        if results:
            for result in results:
                try:
                    func_name = result.function.name
                    func_args = json.loads(result.function.arguments)
                    tool = self.tools[func_name]
                    tool.function(self.agent, message, **func_args)
                except Exception as err:
                    logger.error(f"{err}. 工具 [{func_name}] 调用失败")
            return True
        return False
