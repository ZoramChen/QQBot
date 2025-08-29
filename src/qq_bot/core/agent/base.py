from ncatbot.plugin import BasePlugin
from ncatbot.core import BotClient
from qq_bot.core.tool_manager.base import ToolRegistrarBase


class AgentBase():
    def __init__(self, **kwargs):
        self.bot: BotClient | None = BotClient()
        self.tools: ToolRegistrarBase | None = None
    #
    #     super().__init__(**kwargs)

    async def on_load(self):
        pass

    def register_handlers(self):
        pass

    def run(self):
        pass
