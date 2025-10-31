# import asyncio
# from datetime import datetime
#
# from qq_bot.core.agent.base import AgentBase
# from qq_bot.core.tool_manager.tools.base import ToolBase
# from qq_bot.utils.decorator import tools_logger
# from qq_bot.utils.models import GroupMessageRecord, QUser
# from qq_bot.core import news_provider
# from qq_bot.utils.logging import logger
# from qq_bot.utils.config import settings
#
#
# SOURSE_NAME_LIST = ", ".join(settings.NEWS_SOURCES.keys())
#
#
# @tools_logger
# class DataUpdateTool(ToolBase):
#     tool_name = "news_search"
#     description = {
#         "type": "function",
#         "function": {
#             "name": tool_name,
#             "description": f"收集以下社交平台的新闻或热搜: {SOURSE_NAME_LIST}",
#             "parameters": {
#                 "type": "object",
#                 "required": ["source_name", "news_num"],
#                 "properties": {
#                     "source_name": {
#                         "type": "string",
#                         "description": "目标平台的名称(仅一个)",
#                     },
#                     "news_num": {
#                         "type": "integer",
#                         "description": "要收集的新闻数量。若未提及，则取8",
#                     },
#                 },
#             },
#         },
#         "is_meta": False,
#     }
#
#     @staticmethod
#     def function(
#         agent: AgentBase, user_msg: GroupMessageRecord, source_name: str, news_num: int
#     ) -> bool:
#         async def collect_and_push_news():
#             data = news_provider.get_news(source_name=source_name, max_len=news_num)
#             if data is not None:
#                 actual_source_name, news_list = data
#
#                 news = "\n".join(f"- [{n['title']}]({n['url']})" for n in news_list)
#                 tip = f"当前支持信源 -> {SOURSE_NAME_LIST}"
#                 tip = (
#                     f"未找到{source_name}信源数据，为您选择{actual_source_name}热搜。你也可以重新提问，{tip}"
#                     if actual_source_name != source_name
#                     else tip
#                 )
#
#             else:
#                 actual_source_name = "None"
#                 tip = "None"
#                 news = "新闻/热搜获取失败，API接口异常！"
#
#             template = f"""## 今日热搜
# ------------------
# Source: {actual_source_name}
# Current Time: {datetime.now().strftime("%Y-%m-%d %H:%M %A")}
# Tip: {tip}
# ------------------
#
# {news}
#             """
#             await agent.api.post_group_msg(group_id=user_msg.group_id, text=template)
#
#         try:
#             loop = asyncio.get_event_loop()
#             loop.create_task(collect_and_push_news())
#
#             return True
#         except Exception as err:
#             logger.error(err)
#             return False
