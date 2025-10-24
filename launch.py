# import json
# import ncatbot.utils.literals as literals
#
# literals.PLUGINS_DIR = "src"
#
# from ncatbot.utils.config import config
# from ncatbot.core import BotAPI, BotClient, GroupMessage, PrivateMessage
#
# from qq_bot.utils.logging import logger
# from qq_bot.utils.config import settings
#
#
# if __name__ == "__main__":
#     logger.info(
#         "加载配置文件：\n"
#         f"{json.dumps(settings.model_dump(), indent=4, ensure_ascii=False)}"
#     )
#
#     config.set_bot_uin(settings.BOT_UID)
#     config.set_root(settings.BOT_UID)
#     config.set_ws_uri(settings.BOT_WS_URL)
#     config.set_token("")
#
#     bot = BotClient()
#     bot.run()



# from ncatbot.core import BotClient
#
# bot = BotClient()
#
# if __name__ == "__main__":
#     bot.run(bt_uin="3078805259")


from ncatbot.core import BotClient
from ncatbot.utils import config
from qq_bot.utils.config import settings

config.set_bot_uin(f"{settings.BOT_UID}")
config.set_root(f"{settings.ROOT}")

if __name__ == "__main__":
    BotClient().run(enable_webui_interaction=False)

