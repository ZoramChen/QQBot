import uuid
from sqlmodel import Session, select
from typing import Literal
from qq_bot.utils.models import GroupMessageRecord
from qq_bot.conn.sql.models import GroupMessageV1
from qq_bot.utils.util_text import trans_str
from typing import List
from sqlalchemy import asc


def insert_group_message(
    db: Session,
    message: GroupMessageRecord,
    reply_message: str,
) -> None:
    new_msg = GroupMessageV1(
        message_id=message.str_message_id(),
        group_id=message.str_group_id(),
        sender_id=message.str_sender_id(),
        at_user_id=message.str_at_user_id(),
        message=message.content,
        from_bot=1 if message.from_bot else 0,
        send_time=message.get_datetime(),
        reply_message=reply_message
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)


def insert_group_messages(
    db: Session,
    messages: list[GroupMessageRecord],
    reply_messages: list[str],
) -> None:
    db.bulk_insert_mappings(
        GroupMessageV1,
        [
            {
                "message_id": message.str_message_id(),
                "group_id": message.str_group_id(),
                "sender_id": message.str_sender_id(),
                "at_user_id": message.str_at_user_id(),
                "message": message.str_at_user_id(),
                "from_bot": message.content,
                "send_time": 1 if message.from_bot else 0,
                "reply_message": reply_message,
            }
            for message,reply_message in zip(messages,reply_messages)
        ],
    )
    db.commit()

def fetch_all_group_messages(db: Session) -> List[GroupMessageV1]:
    """
    读取 private_message_v1 全表数据，按 id 升序排列，
    返回 PrivateMessageRecord 列表。
    """
    stmt = select(GroupMessageV1).order_by(asc(GroupMessageV1.id))
    rows = db.exec(stmt).all()
    return list(rows)