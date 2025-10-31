# import asyncio
# from qq_bot.core.agent.agent_server import update_group_user_info
# from qq_bot.core.agent.base import AgentBase
# from qq_bot.core.tool_manager.tools.base import ToolBase
# from qq_bot.utils.decorator import tools_logger
# from qq_bot.utils.models import GroupMessageRecord, QUser
# from qq_bot.utils.logging import logger
#
#
# @tools_logger
# class MemberUpdateTool(ToolBase):
#     tool_name = "member_update"
#     description = {
#         "type": "function",
#         "function": {
#             "name": tool_name,
#             "description": "更新群组内某个群员（或全员）的数据",
#             "parameters": {
#                 "type": "object",
#                 "required": ["user"],
#                 "properties": {
#                     "user": {
#                         "type": "array",
#                         "items": {
#                             "type": "string",
#                             "description": "单个用户名。如果为 'ALL'，表示更新所有用户信息",
#                         },
#                         "description": "要被更新的用户名列表，或仅包含一个 'ALL' 表示更新全员",
#                     },
#                 },
#             },
#             "is_meta": False,
#         },
#     }
#
#     @staticmethod
#     def function(agent: AgentBase, user_msg: GroupMessageRecord, user: list[str]) -> bool:
#         async def collect_and_update_gruop_user_info():
#             target_users: list[QUser] = []
#
#             # 收集目标用户数据
#             response = await agent.api.get_group_member_list(user_msg.group_id, False)
#             if response["status"] == "ok":
#                 if "ALL" not in user:
#                     target_users = [
#                         QUser.from_dict(u)
#                         for u in response["data"]
#                         if u["nickname"] in user
#                     ]
#                 else:
#                     target_users = [QUser.from_dict(u) for u in response["data"]]
#
#             updated_users, inserted_users = update_group_user_info(users=target_users)
#
#             # 发送提示信息
#             text = (
#                 f"已更新成员信息\n"
#                 f"更新主体: {(', '.join(updated_users[:4]) + ('' if len(updated_users) < 4 else '等')) if updated_users else 'None'}\n"
#                 f"新增主体: {(', '.join(inserted_users[:4]) + ('' if len(inserted_users) < 4 else '等')) if inserted_users else 'None'}\n"
#             )
#             await agent.api.post_group_msg(
#                 group_id=user_msg.group_id, at=user_msg.sender.id, text=text
#             )
#
#         try:
#             loop = asyncio.get_event_loop()
#             loop.create_task(collect_and_update_gruop_user_info())
#
#             return True
#         except Exception as err:
#             logger.error(err)
#             return False
