from qq_bot.core.agent.base import AgentBase
from qq_bot.utils.models import GroupMessageRecord
from ncatbot.plugin import BasePlugin


class ToolBase:
    tool_name: str
    description: dict

    @staticmethod
    def function(bot: BasePlugin, **kwargs) -> bool:
        pass
