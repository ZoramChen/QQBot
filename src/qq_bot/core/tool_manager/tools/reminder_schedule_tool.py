import asyncio
from ncatbot.core import BotAPI
from sqlmodel import Session
from qq_bot.core.agent.agent_server import send_msg_2_group
from qq_bot.core.agent.base import AgentBase
from qq_bot.conn.sql.crud.user_crud import select_user_by_name
from qq_bot.core.tool_manager.tools.base import ToolBase
from qq_bot.utils.decorator import sql_session, tools_logger
from qq_bot.utils.models import GroupMessageRecord
from qq_bot.utils.util_text import trans_int
from qq_bot.utils.logging import logger


@tools_logger
class ReminderScheduleTool(ToolBase):
    tool_name = "reminder_schedule"
    description = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": "定时提醒某人要做某事（必须包含被提醒人、时间、提醒事项三个要素）",
            "parameters": {
                "type": "object",
                "required": ["user", "time", "message"],
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "你要提醒的那位用户的昵称",
                    },
                    "time": {
                        "type": "string",
                        "description": "何时提醒（注意分析时间），时间一定是具体数值，不能是明天，后天等模糊时间，遵循格式：YYYY-MM-DD HH:MM:SS",
                    },
                    "message": {
                        "type": "string",
                        "description": "被提醒人需要完成的事项，语气要稍微可爱一点",
                    },
                },
            },
        },
        "is_meta": False,
    }

    # @staticmethod
    # def function(
    #     agent: AgentBase,
    #     user_msg: GroupMessageRecord,
    #     user: str,
    #     time: str,
    #     message: str,
    # ) -> bool:
    #     def send_message_to_user_wrapper():
    #         @sql_session
    #         async def send_message_to_user(db: Session):
    #             # 查找用户ID
    #             # umodel = select_user_by_name(db=db, name=user)
    #             # uid = trans_int(umodel.id) if umodel else None
    #
    #             uid: int | None = None
    #             response = await agent.api.get_group_member_list(user_msg.group_id)
    #             if response["status"] == "ok":
    #                 uid = next(
    #                     (
    #                         umodel["user_id"]
    #                         for umodel in response["data"]
    #                         if umodel["nickname"] == user
    #                     ),
    #                     None,
    #                 )
    #
    #             text = f"{message}\n"
    #             if uid is None:
    #                 text = f"TO: {user}\n{message}"
    #
    #             # 发送消息
    #             result = await agent.api.post_group_msg(
    #                 group_id=user_msg.group_id, at=uid, text=text
    #             )
    #             if result["status"] == "ok":
    #                 logger.info(f"定时提醒已触发: [主体 - {user}]{time} -> {message}")
    #             else:
    #                 logger.error(f"定时提醒发送失败: [主体 - {user}]{time} -> {message}")
    #
    #         asyncio.get_event_loop().create_task(send_message_to_user())
    #         # asyncio.create_task(send_message_to_user())
    #
    #     try:
    #         # 添加定时任务
    #         agent.add_scheduled_task(
    #             job_func=send_message_to_user_wrapper,
    #             name="定时提醒",
    #             interval=time,
    #             # kwargs=
    #         )
    #
    #         # 发送提示信息
    #         asyncio.get_event_loop().create_task(
    #             agent.api.post_group_msg(
    #                 group_id=user_msg.group_id,
    #                 text=f"已建立日程提醒任务\n主体人: {user}\nTime: {time}\nTheme: {user_msg.content}\n",
    #                 at=user_msg.sender.id,
    #             )
    #         )
    #
    #         return True
    #     except Exception as err:
    #         logger.error(err)
    #         return False
    @staticmethod
    async def group_msg_function(
            group_id: int,
            content: str,
            api: BotAPI | None = None,
    ) -> None:
        await api.post_group_msg(group_id, content)

    @staticmethod
    async def private_msg_function(
            user_id: int,
            content: str,
            api: BotAPI | None = None,
    ) -> None:
        await api.post_private_msg(user_id, content)
        # def send_message_to_user_wrapper():
        #     @sql_session
        #     async def send_message_to_user(db: Session):
        #         # 查找用户ID
        #         # umodel = select_user_by_name(db=db, name=user)
        #         # uid = trans_int(umodel.id) if umodel else None
        #
        #         uid: int | None = None
        #         response = await agent.api.get_group_member_list(user_msg.group_id)
        #         if response["status"] == "ok":
        #             uid = next(
        #                 (
        #                     umodel["user_id"]
        #                     for umodel in response["data"]
        #                     if umodel["nickname"] == user
        #                 ),
        #                 None,
        #             )
        #
        #         text = f"{message}\n"
        #         if uid is None:
        #             text = f"TO: {user}\n{message}"
        #
        #         # 发送消息
        #         result = await agent.api.post_group_msg(
        #             group_id=user_msg.group_id, at=uid, text=text
        #         )
        #         if result["status"] == "ok":
        #             logger.info(f"定时提醒已触发: [主体 - {user}]{time} -> {message}")
        #         else:
        #             logger.error(f"定时提醒发送失败: [主体 - {user}]{time} -> {message}")
        #
        #     asyncio.get_event_loop().create_task(send_message_to_user())
        #     # asyncio.create_task(send_message_to_user())
        #
        # try:
        #     # 添加定时任务
        #     agent.add_scheduled_task(
        #         job_func=send_message_to_user_wrapper,
        #         name="定时提醒",
        #         interval=time,
        #         # kwargs=
        #     )
        #
        #     # 发送提示信息
        #     asyncio.get_event_loop().create_task(
        #         agent.api.post_group_msg(
        #             group_id=user_msg.group_id,
        #             text=f"已建立日程提醒任务\n主体人: {user}\nTime: {time}\nTheme: {user_msg.content}\n",
        #             at=user_msg.sender.id,
        #         )
        #     )
        #
        #     return True
        # except Exception as err:
        #     logger.error(err)
        #     return False