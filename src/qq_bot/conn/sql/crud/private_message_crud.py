import uuid
from sqlmodel import Session, select
from typing import Literal
from qq_bot.utils.models import PrivateMessageRecord
from qq_bot.conn.sql.models import PrivateMessageV1
from qq_bot.utils.util_text import trans_str
from typing import List
from sqlmodel import Session, select
from sqlalchemy import asc

def insert_private_message(
    db: Session,
    message: PrivateMessageRecord,
    reply_message: str,
) -> None:
    new_msg = PrivateMessageV1(
        message_id=message.str_id(),
        sender_id=message.str_user_id(),
        message=message.content,
        from_bot=1 if message.from_bot else 0,
        send_time=message.get_datetime(),
        reply_message=reply_message,
    )
    db.add(new_msg)
    db.commit()
    db.refresh(new_msg)


def insert_private_messages(
    db: Session,
    messages: list[PrivateMessageRecord],
    reply_messages: list[str],
) -> None:
    db.bulk_insert_mappings(
        PrivateMessageV1,
        [
            {
                "message_id": message.str_id(),
                "sender_id": message.str_user_id(),
                "message": message.content,
                "from_bot": 1 if message.from_bot else 0,
                "send_time": message.get_datetime(),
                "reply_message": reply_message,
            }
            for message,reply_message in zip(messages,reply_messages)
        ],
    )
    db.commit()

def fetch_all_private_messages(db: Session) -> List[PrivateMessageV1]:
    """
    读取 private_message_v1 全表数据，按 id 升序排列，
    返回 PrivateMessageRecord 列表。
    """
    stmt = select(PrivateMessageV1).order_by(asc(PrivateMessageV1.id))
    rows = db.exec(stmt).all()
    return list(rows)
