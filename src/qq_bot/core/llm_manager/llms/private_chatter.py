from collections import defaultdict
from datetime import datetime
import chromadb
import re
import time
import json
import os
import ast
import asyncio
from typing import Any, Optional
from itertools import chain
from ncatbot.core import BotAPI
from ncatbot.plugin import BasePlugin
from sqlmodel import Session
from openai.types.chat import ChatCompletionSystemMessageParam

from qq_bot.conn.chroma.base import ChromaEmbeddingFunction, is_id_exists, message_add, messages_query
from qq_bot.utils.decorator import sql_session
from qq_bot.utils.models import PrivateMessageRecord, QUser
from qq_bot.utils.util import search_meme
from qq_bot.utils.util_text import parse_text,time_trans_int
from qq_bot.core.llm_manager.llms.base import OpenAIBase
from qq_bot.conn.sql.crud.private_message_crud import fetch_all_private_messages
from qq_bot.conn.sql.crud.user_crud import fetch_all_users_info, insert_users,update_users
from qq_bot.utils.config import settings
from qq_bot.utils.logging import logger
from qq_bot.conn.sql.session import LocalSessionSync



class LLMPrivateChatter(OpenAIBase):
    __model_tag__ = settings.PRIVATE_CHATTER_LLM_CONFIG_NAME

    def __init__(
        self,
        base_url: str,
        api_key: str,
        prompt_path: str,
        bot: BasePlugin,
        max_retries: int = 3,
        retry: int = 3,
        **kwargs,
    ) -> None:
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            prompt_path=prompt_path,
            max_retries=max_retries,
            retry=retry,
            bot=bot,
            **kwargs,
        )
        self.cache_len = self.configs.get("message_cache_len", 20)
        # 群组id 对应的历史消息集合cache
        self.user_cache: dict[int, list[PrivateMessageRecord]] = defaultdict(list)
        # 消息id 对应的模型回复消息
        self.llm_cache: dict[int, str] = {}
        # 用户id 对应的用户信息
        self.user_info: dict[int, QUser] = {}
        # 用户id 对应的用户个性化系统prompt
        self.user_system_prompt: dict[int, ChatCompletionSystemMessageParam] = {}
        chroma_client = chromadb.PersistentClient(path="./chromadb")


        try:
            self.chroma_collection = chroma_client.get_collection(
                name=settings.CHROMADB_PRIVATE_MSG_COLLECTION,
                embedding_function=ChromaEmbeddingFunction(
                    model_name=settings.EMBEDDING_MODEL,
                    base_url=settings.EMBEDDING_BASE_URL,
                    api_key=settings.EMBEDDING_API_KEY,
                )
            )
        except Exception as e:
            self.chroma_collection = chroma_client.create_collection(
                name=settings.CHROMADB_PRIVATE_MSG_COLLECTION,
                embedding_function=ChromaEmbeddingFunction(
                    model_name=settings.EMBEDDING_MODEL,
                    base_url=settings.EMBEDDING_BASE_URL,
                    api_key=settings.EMBEDDING_API_KEY,
                )
            )


        self._load_mysql_data()

    @sql_session
    def _load_mysql_data(self, db: Session | None = None):
        # 加载聊天记录
        message_rows = fetch_all_private_messages(db)
        for row in message_rows:
            self.insert_and_update_history_message(
                user_message=PrivateMessageRecord(
                    message_id=int(row.message_id),
                    user_id=int(row.sender_id),
                    content=row.message,
                    from_bot=bool(row.from_bot),
                    send_time=str(row.send_time),
                ),
                llm_message=row.reply_message
            )

        # 加载账户信息
        user_rows = fetch_all_users_info(db)
        for row in user_rows:
            self.user_info[int(row.user_id)] = QUser(
                user_id=int(row.user_id),
                nikename=row.nikename,
                sex=row.sex,
                age=row.age,
                long_nick=row.long_nick,
                location=row.location,
                update_time=time_trans_int(str(row.update_time)),
            )


    def get_history_message(self, user_id: int) -> list:
        result = []
        for u_msg in self.user_cache[user_id]:
            result.append(
                self.format_user_message(
                    content=u_msg.content, name=str(u_msg.user_id)[:6]
                )
            )
            l_msg: str | None = self.llm_cache.get(u_msg.message_id, None)
            if l_msg:
                result.append(self.format_llm_message(l_msg))
        return result

    def insert_and_update_history_message(
        self, user_message: PrivateMessageRecord, llm_message: str | None = None
    ) -> None:
        group_user_cache = self.user_cache[user_message.user_id]

        # 避免重复插入
        if any(msg.message_id == user_message.message_id for msg in group_user_cache):
            return

        if len(group_user_cache) >= self.cache_len:
            # 记忆长度超出，推出
            removed_msg = group_user_cache.pop(0)
            pop_llm_message = self.llm_cache.pop(removed_msg.message_id, "")
            if not is_id_exists(self.chroma_collection,str(removed_msg.message_id)):
                message_add(
                    collection=self.chroma_collection,
                    document=f"{removed_msg.send_time}|{str(removed_msg.user_id)[:6]}|{removed_msg.content}\nassistant|{pop_llm_message}",
                    id=str(removed_msg.message_id),
                    metadata={"user_id": str(removed_msg.user_id)}
                )
        group_user_cache.append(user_message)

        # 避免插入空值、避免重复插入
        if (llm_message is not None) and (user_message.message_id not in self.llm_cache.keys()):
            self.llm_cache[user_message.message_id] = llm_message

        logger.info(
            f"[{self.__model_tag__}]: 短期记忆已更新 USER[{user_message.content}]"
            f"{' -> LLM[' + llm_message + ']' if llm_message else ''}"
        )

    async def update_users_info(
            self, user_id: int,api: BotAPI | None = None,
    ) -> None:
        if user_id not in self.user_info:
            sender = await QUser.from_private(user_id, api)
            self.user_info[user_id] = sender
            self.update_user_system_prompt(user_id)
            with LocalSessionSync() as db:
                insert_users(db, sender)
        elif  int(time.time()) - self.user_info[user_id].update_time >= 60:
            await QUser.update_private(self.user_info[user_id], api)
            self.update_user_system_prompt(user_id)
            with LocalSessionSync() as db:
                update_users(db, [self.user_info[user_id]])

    def update_user_system_prompt(self, user_id: int) -> None:
        temp_system_prompt = "You are a helpful assistant."
        if user_id in self.user_info:
            temp_system_prompt = self._set_prompt(
                input={
                    "nick": self.user_info[user_id].nikename,
                    "age": self.user_info[user_id].age,
                    "sex": self.user_info[user_id].sex,
                    "location": self.user_info[user_id].location,
                },
                prompt=self.custom_system_prompt
            )
        self.user_system_prompt[user_id] = ChatCompletionSystemMessageParam(
            content=temp_system_prompt,
            role="system",
        )


    def reduce_token(chatbot, system, context, myKey):
        context.append(
            {
                "role": "user",
                "content": "请帮我总结一下上述对话的内容，实现减少tokens的同时，保证对话的质量。在总结中不要加入这一句话。",
            }
        )

        response = None  # get_response(system, context, myKey, raw=True)

        statistics = f'本次对话Tokens用量【{response["usage"]["completion_tokens"]+12+12+8} / 4096】'
        optmz_str = parse_text(
            f'好的，我们之前聊了:{response["choices"][0]["message"]["content"]}\n\n================\n\n{statistics}'
        )
        chatbot.append(
            (
                "请帮我总结一下上述对话的内容，实现减少tokens的同时，保证对话的质量。",
                optmz_str,
            )
        )

        context = []
        context.append({"role": "user", "content": "我们之前聊了什么?"})
        context.append(
            {
                "role": "assistant",
                "content": f'我们之前聊了：{response["choices"][0]["message"]["content"]}',
            }
        )
        return chatbot, context

    def standardize_llm_messages(self, content: str) -> list[dict]:
        def _extract_meme(temp_content: str) -> tuple[list,str]:
            # 提取所有 [] 里的内容（不含括号本身）
            tags = re.findall(r'\[(.*?)\]', temp_content)
            cleaned = re.sub(r'\[.*?\]', '', temp_content)
            return tags,cleaned
        memes,content = _extract_meme(content)
        if memes:
            meme_urls = search_meme(memes[0])
            if meme_urls:
                return [{"type":"image","content":meme_urls[0]},{"type":"text", "content":content}]
            else:
                return [{"type":"text", "content":content}]
        else:
            return [{"type":"text", "content":content}]



    async def run(self, message: PrivateMessageRecord, **kwargs) -> str | dict | None:
        user_id = message.user_id
        user_message = message.content

        history: list = self.get_history_message(user_id)

        related_msgs = messages_query(self.chroma_collection,user_message,conditions={"user_id": str(user_id)})
        history.append(
            {"role": "system", "content": related_msgs}
        )
        history.append(
            self.format_user_message(
                content=self._set_prompt(
                    input={
                        "text": user_message,
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M %A"),
                    }
                ),
                name=str(message.user_id)[:6],
            )
        )
        if settings.MCP_ACTIVATE:
            llm_message = await self._async_tool_inference(user_id=user_id,content=history, custom_system_prompt=self.user_system_prompt.get(user_id,None), **kwargs)
        else:
            llm_message = await self._async_inference(content=history, custom_system_prompt=self.user_system_prompt.get(user_id,None), **kwargs)
        # if llm_message and llm_message.tool_calls:
        #     tool_call = llm_message.tool_calls[0]
        #     # 获取函数调用的参数
        #     args = json.loads(tool_call.function.arguments)
        #     content = llm_message.content
        #     self.insert_and_update_history_message(message, content)
        #     return {
        #         "name":tool_call.function.name,
        #         "args":args,
        #         "content":content
        #     }
        if llm_message and llm_message.content:
            self.insert_and_update_history_message(message, llm_message.content)
            return llm_message.content
        return None



