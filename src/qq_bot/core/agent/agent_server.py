import asyncio
import random
from ncatbot.core import GroupMessage, BotAPI
from sqlmodel import Session
from qq_bot.conn.sql.crud.user_crud import (
    insert_users,
    select_user_by_ids,
    update_users,
)
from qq_bot.core.agent.base import AgentBase
from qq_bot.utils.decorator import sql_session
from qq_bot.utils.models import GroupMessageRecord, PrivateMessageRecord, QUser
from qq_bot.utils.util_text import (
    auto_split_sentence,
    language_classifity,
    typing_time_calculate,
)
from qq_bot.conn.sql.crud.group_message_crud import (
    insert_group_message,
    insert_group_messages,
)
from qq_bot.conn.sql.crud.private_message_crud import (
    insert_private_message,
    insert_private_messages,
)

from qq_bot.core import llm_registrar
from qq_bot.utils.config import settings
from qq_bot.utils.logging import logger


@sql_session
def save_group_msg_2_sql(
    messages: list[GroupMessageRecord] | GroupMessageRecord,
    reply_messages: list[str] | str,
    db: Session | None = None,
) -> None:
    try:
        abs: str = ""
        if isinstance(messages, list):
            insert_group_messages(db=db, messages=messages,reply_messages=reply_messages)
            abs = ", ".join([f"{i.content[:4]}.." for i in messages])
        elif isinstance(messages, GroupMessageRecord):
            insert_group_message(db=db, message=messages,reply_message=reply_messages)
            abs = f"{messages.content[:5]}.."
        else:
            return
        logger.info(f"聊天记录已存储: {abs}")
    except Exception as err:
        logger.error(f"{err}. 聊天记录存储失败: {abs}")

@sql_session
def save_private_msg_2_sql(
        messages: list[PrivateMessageRecord] | PrivateMessageRecord,
        reply_messages: list[str] | str,
        db: Session | None = None,
) -> None:
    try:
        abs: str = ""
        if isinstance(messages, list):
            insert_private_messages(db=db, messages=messages,reply_messages=reply_messages)
            abs = ", ".join([f"{i.content[:4]}.." for i in messages])
        elif isinstance(messages, PrivateMessageRecord):
            insert_private_message(db=db, message=messages,reply_message=reply_messages)
            abs = f"{messages.content[:5]}.."
        else:
            return
        logger.info(f"聊天记录已存储: {abs}")
    except Exception as err:
        logger.error(f"{err}. 聊天记录存储失败: {abs}")


@sql_session
def update_group_user_info(
    users: list[QUser], db: Session | None = None
) -> tuple[list, list]:
    updated_users: list[str] = []
    inserted_users: list[str] = []

    try:
        # 更新已有数据
        existed_users = select_user_by_ids(db=db, ids=[u.id for u in users])
        update_users(db=db, users=existed_users, updated_users=users)
        updated_users = [u.nikename for u in existed_users]
        logger.info(f"更新群组用户[{len(existed_users)}]条: {updated_users}")
    except Exception as err:
        logger.error(f"更新群组用户时发生错误: {err}")

    try:
        # 插入新数据
        existed_users_id = {int(u.id) for u in existed_users}  # 使用 set 来加速查找
        new_users: list[QUser] = [u for u in users if int(u.id) not in existed_users_id]
        insert_users(db=db, users=new_users)
        inserted_users = [u.nikename for u in new_users]
        logger.info(f"新增群组用户[{len(new_users)}条]: {inserted_users}")
    except Exception as err:
        logger.error(f"新增群组用户时发生错误: {err}")

    return updated_users, inserted_users


async def send_msg_2_group(
    api: BotAPI, group_id: int, text: str, **kwargs
) -> GroupMessageRecord | None:
    result: dict = await api.post_group_msg(group_id=group_id, text=text, **kwargs)

    if result.get("status") != "ok" or not result.get("data"):
        return None

    msg_id = result["data"].get("message_id", -1)
    reply_data = await api.get_msg(msg_id)

    if reply_data.get("status") != "ok" or not reply_data.get("data"):
        return None

    return await GroupMessageRecord.from_group_message(
        GroupMessage(reply_data["data"]), True
    )


async def group_random_chat(
    api: BotAPI,
    message: GroupMessageRecord,
    prob: float,
    need_split: bool = True,
) -> bool:
    # 概率触发聊天
    real_prob = random.random()
    if real_prob < prob:
        logger.info(f"回复意愿达标 [{prob:.2f}({real_prob:.2f}) / 1.0]")

        llm: LLMGroupChatter = llm_registrar.get(settings.GROUP_CHATTER_LLM_CONFIG_NAME)
        bot_reply: str | None = await llm.run(message)

        if not bot_reply:
            return False

        if need_split:
            bot_messages: list[GroupMessageRecord] = []
            language = language_classifity(bot_reply)
            parts: list[str] = auto_split_sentence(bot_reply, language)

            for part in parts:
                part = part.strip("。.~～")
                await asyncio.sleep(typing_time_calculate(part, language))
                bot_reply = await send_msg_2_group(api, message.group_id, part, reply=message.id)
                if bot_reply:
                    bot_messages.append(bot_reply)
            save_group_msg_2_sql(messages=bot_messages)
        else:
            await asyncio.sleep(typing_time_calculate(bot_reply, language))
            bot_message = await send_msg_2_group(api, message.group_id, bot_reply, reply=message.id)
            if bot_message is not None:
                save_group_msg_2_sql(messages=bot_message)

        return True

    return False
