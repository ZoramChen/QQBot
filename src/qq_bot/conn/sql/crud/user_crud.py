from cachetools.keys import hashkey
from sqlmodel import Session, col, select
from cachetools import LRUCache, cached
from qq_bot.conn.sql.models import UserV1
from qq_bot.utils.models import QUser
from qq_bot.utils.util_text import trans_int, trans_str

_user_by_name_cache: LRUCache[str, str] = LRUCache(maxsize=1024 * 10)
_user_by_id_cache: LRUCache[str, str] = LRUCache(maxsize=1024 * 10)


@cached(_user_by_name_cache, key=lambda db, user_id: str(hashkey(user_id)))  # noqa
def select_user_by_id(db: Session, user_id: int) -> UserV1 | None:
    result = db.exec(select(UserV1).where(UserV1.user_id == str(user_id))).first()
    return result


def select_user_by_ids(db: Session, ids: list[int]) -> list[UserV1]:
    result = db.exec(select(UserV1).where(col(UserV1.id).in_(ids))).all()
    return list(result)


@cached(_user_by_id_cache, key=lambda db, name: str(hashkey(name)))  # noqa
def select_user_by_name(db: Session, name: str) -> UserV1 | None:
    result = db.exec(select(UserV1).where(UserV1.nikename == str(name))).first()
    return result


def insert_users(db: Session, users: list[QUser] | QUser) -> None:
    data: list[QUser] = users if isinstance(users, list) else [users]

    db.bulk_insert_mappings(UserV1, [user.to_dict() for user in data])
    db.commit()


def update_users(
        db: Session,
        updated_users: list[QUser]
) -> None:
    if not updated_users:
        return

    # 1. 把 QUser 转成 id -> QUser 映射
    q_map = {int(q.user_id): q for q in updated_users}

    # 2. 一次性查出已存在的 UserV1
    existing = {
        int(u.user_id): u
        for u in db.exec(
            select(UserV1).where(UserV1.user_id.in_(map(str, q_map.keys())))
        ).all()
    }

    # 3. 更新或新增
    to_flush = []
    for uid, q_user in q_map.items():
        user = existing.get(uid)
        if user is None:
            # 数据库里没有就新建
            user = UserV1(user_id=str(uid))
            db.add(user)
        # 同步字段
        for field, value in q_user.to_dict().items():
            setattr(user, field, value)
        to_flush.append(user)

    # 4. 清缓存
    for q_user in updated_users:
        _user_by_name_cache.pop(str(hashkey(q_user.nikename)), None)
        _user_by_id_cache.pop(str(hashkey(q_user.user_id)), None)

    # 5. 一次性 flush + commit
    db.add_all(to_flush)
    db.commit()

def fetch_all_users_info(db: Session) -> list[UserV1]:
    """
    读取 private_message_v1 全表数据，按 id 升序排列，
    返回 PrivateMessageRecord 列表。
    """
    stmt = select(UserV1)
    rows = db.exec(stmt).all()
    return list(rows)
