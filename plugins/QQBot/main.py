from ncatbot.core import GroupMessage, PrivateMessage, MessageChain, Face, BaseMessage
import hashlib
from ncatbot.plugin import CompatibleEnrollment
from qq_bot.core.llm_manager.llm_registrar import get_llm_registrar

from qq_bot.core.tool_manager.tool_registrar import ToolRegistrar
from qq_bot.core.mcp_manager.mcp_register import get_mcp_register
from qq_bot.core.agent.agent_command import (
    group_at_chat,
    group_at_reply,
    group_random_picture,
    group_random_setu,
    group_use_tool,
)
from qq_bot.core.agent.agent_server import save_group_msg_2_sql,save_private_msg_2_sql
# from qq_bot.core import llm_registrar
from qq_bot.utils.models import GroupMessageRecord,PrivateMessageRecord
from qq_bot.utils.logging import logger
from qq_bot.utils.config import settings

bot = CompatibleEnrollment
from ncatbot.plugin import BasePlugin

class QQBot(BasePlugin):
    name = "QQBot"  # 插件名称
    version = "0.1.1"  # 插件版本

    async def init(self, **kwargs) -> None:
        logger.info(f"加载插件")
        self.tools = ToolRegistrar(agent=self)

        # 指令（**检测有顺序区分**）
        self.group_command = [
            group_random_picture,
            group_random_setu,
            group_use_tool,
            group_at_reply,
            group_at_chat,
        ]
        self.tools_description = [self.tools.tools["reminder_schedule"].description]
        self.llm_registrar = await get_llm_registrar(self)

    async def on_load(self):
        await self.init()
        print(f"{self.name} 插件已加载")
        print(f"插件版本: {self.version}")
        self.register_handlers()

        self.register_user_func(
            name="ZoeHelp",
            handler=self.zoe_help,
            filter=lambda event: (
                    isinstance(event, PrivateMessage) and
                    event.raw_message.lower().startswith("/zoehelp")
            ),
            description="获取Zoe信息",
            usage="/zoehelp",
            examples=["/zoehelp", "/ZoeHelp", "/ZOEHELP"],
            tags=["zoehelp"],
        )

    async def zoe_help(self, msg: BaseMessage):
        reply = ("喵呜～主人敲敲Zoe的小脑袋，就能解锁4项专属技能喵✨\n"
                 "1.🌦️全球天气秒查，晴雨都陪主人贴贴～\n"
                 "2.🚄车票嗅嗅，余票时刻一手抓，出行不慌喵！\n"
                 "3.⏰定时卖萌提醒，到点“喵——”叫醒主人，比心💗\n"
                 "4.🌐联网小鱼干搜索，新鲜答案立刻叼回来～\n"
                 "随时@Zoe，她摇尾巴秒出现，只对主人专喵🐾\n")
        await msg.reply(text=reply)

    async def on_close(self):
        print(f"[{self.name}] 开始执行自定义退出逻辑...")
        mcp_tools = await get_mcp_register()
        await mcp_tools.disconnect()

    def register_handlers(self):
        @bot.startup_event()
        async def run_notice():
            message = MessageChain([
                "ncatbot 启动！"
            ])
            await self.api.post_private_msg(settings.ROOT, rtf=message)


        @bot.group_event()
        async def on_group_message(msg: GroupMessage):
            if msg.post_type != "message":
                logger.warning(f"非文本消息，跳过")
                return
            user_msg = await GroupMessageRecord.from_group_message(msg, False)
            cur_model = self.llm_registrar.get(
                settings.GROUP_CHATTER_LLM_CONFIG_NAME
            )
            tools=[self.tools.tools["reminder_schedule"].description]
            if user_msg.content != "":
                # 获取大模型回答
                res= await cur_model.run(user_msg,tools=tools)
                # 如果是文本类回答
                if isinstance(res, str):
                    await msg.reply(text=res)
                    save_group_msg_2_sql(messages=user_msg,reply_messages=res)
                # 如果是function call
                elif isinstance(res, dict):
                    if res["name"] == "reminder_schedule":
                        args = res["args"]
                        await self.api.post_group_msg(group_id=user_msg.group_id,text=res["content"])
                        self.add_scheduled_task(
                            job_func=self.tools.tools["reminder_schedule"].group_msg_function,
                            name=hashlib.md5(str(res["args"]).encode("utf-8")).hexdigest(),
                            interval=args["time"],
                            kwargs={"group_id":user_msg.group_id,"content":f"{args['user']},{args['message']}","api":self.api},
                        )
                        save_group_msg_2_sql(messages=user_msg,reply_messages=res["content"])

        @bot.private_event()
        async def on_private_message(msg: PrivateMessage):
            if msg.post_type != "message":
                logger.warning(f"非文本消息，跳过")
                return
            user_msg = await PrivateMessageRecord.from_private_message(msg, False)
            if user_msg.content.lower().startswith("/zoehelp"):
                return
            cur_model = self.llm_registrar.get(
                settings.PRIVATE_CHATTER_LLM_CONFIG_NAME
            )
            logger.info(f"{user_msg.user_id}发来消息：{user_msg.content}")
            await cur_model.update_users_info(user_msg.user_id,self.api)
            if user_msg.content != "":
                # 获取大模型回答
                res = await cur_model.run(user_msg)
                # 如果是文本类回答
                if isinstance(res, str):
                    format_message = cur_model.standardize_llm_messages(res)

                    for d in format_message:
                        if d["type"] =="text":
                            await msg.reply(text=d["content"])
                        elif d["type"] == "image":
                            # await self.bot.api.post_private_msg(msg.user_id, image=d["content"])
                            await msg.reply(image=d["content"],is_file=True)
                    logger.info(f"{user_msg.user_id}回复消息：{str(format_message)}")
                    save_private_msg_2_sql(messages=user_msg,reply_messages=res)




#     def run(self):
#         self.bot.run(bt_uin=settings.BOT_UID,root=settings.ROOT)
#
#
# if __name__ == "__main__":
#     bot = QQBot()
#     bot.run()
