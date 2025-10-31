from ncatbot.core import BotClient
from ncatbot.utils import config
from qq_bot.utils.config import settings

config.set_bot_uin(settings.BOT_UID)
config.set_root(settings.ROOT)
config.set_ws_uri(settings.WS_URL)
config.set_ws_token(settings.WS_TOKEN)

if __name__ == "__main__":
    BotClient().run(enable_webui_interaction=False)

