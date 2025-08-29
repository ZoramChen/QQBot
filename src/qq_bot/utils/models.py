from datetime import datetime
from pydantic import BaseModel
from ncatbot.core import BotAPI, GroupMessage, PrivateMessage
import time
from qq_bot.conn.sql.models import UserV1
from qq_bot.utils.util_text import trans_int, trans_str, time_trans_str


class QUser(BaseModel):
    user_id: int
    nikename: str | None = None
    sex: str | None = None
    age: int | None = None
    long_nick: str | None = None
    location: str | None = None
    update_time: int

    @classmethod
    async def from_group(
        cls,
        user_id: int,
        group_id: int,
        nikename: str | None = None,
        api: BotAPI | None = None,
    ) -> "QUser":
        if (
            api
            and (
                at_user_info := await api.get_group_member_info(
                    group_id=group_id, user_id=user_id, no_cache=False
                )
            )
            and at_user_info["status"] == "ok"
        ):
            return cls(
                user_id=at_user_info["data"]["user_id"],
                nikename=at_user_info["data"]["nikename"],
                sex=at_user_info["data"]["sex"],
                age=at_user_info["data"]["age"],
                update_time=int(time.time())
            )
        return cls(user_id=user_id, nikename=nikename,update_time=int(time.time()))


    @classmethod
    async def from_private(
            cls,
            user_id: int,
            api: BotAPI | None = None,
    ) -> "QUser":
        if (
                api
                and (
                at_user_info := api.get_stranger_info_sync(user_id=user_id)
        )
                and at_user_info["status"] == "ok"
        ):
            return cls(
                user_id=at_user_info["data"]["user_id"],
                nikename=at_user_info["data"]["nick"],
                sex=at_user_info["data"]["sex"],
                age=at_user_info["data"]["age"],
                long_nick=at_user_info["data"]["longNick"],
                location=f"{at_user_info['data']['country']}{at_user_info['data']['province']}{at_user_info['data']['city']}",
                update_time=int(time.time())
            )
        return cls(user_id=user_id,update_time=int(time.time()))

    @classmethod
    async def update_private(
            cls,
            q: "QUser",
            api: BotAPI | None = None,
    ):
        if (
                api
                and (
                at_user_info := await api.get_stranger_info(user_id=q.user_id)
        )
                and at_user_info["status"] == "ok"
        ):
            q.nikename=at_user_info["data"]["nick"]
            q.sex=at_user_info["data"]["sex"]
            q.age=at_user_info["data"]["age"]
            q.long_nick=at_user_info["data"]["longNick"]
            q.location=f"{at_user_info['data']['country']}{at_user_info['data']['province']}{at_user_info['data']['city']}"
            q.update_time=int(time.time())



    @classmethod
    async def from_sql_model(cls, data: UserV1 | None) -> "QUser":
        return (
            cls(
                user_id=trans_int(data.user_id),
                nikename=data.nikename,
                sex=data.sex,
                age=data.age,
                long_nick=data.long_nick,
            )
            if data
            else None
        )

    @classmethod
    def from_dict(cls, data: dict) -> "QUser":
        return cls(
            user_id=trans_int(data.get("user_id", None) or data.get("user_id", None)),
            nikename=data.get("nickname", "QQ用户"),
            sex=data.get("sex", "unknown"),
            age=data.get("age", 0),
            long_nick=data.get("long_nick", None),
        )

    def to_dict(self, to_str: bool = True) -> dict:
        return {
            "user_id": trans_str(self.user_id) if to_str else self.user_id,
            "nikename": self.nikename,
            "sex": self.sex,
            "age": self.age,
            "long_nick": self.long_nick,
            "location": self.location,
            "update_time": time_trans_str(self.update_time),
        }


class GroupMessageRecord(BaseModel):
    message_id: int
    content: str
    group_id: int
    sender_id: int
    at_user_id: int | None = None
    from_bot: bool
    send_time: str
    # reply_message_id: int | None = None

    def get_datetime(self) -> datetime:
        return datetime.fromisoformat(self.send_time)

    def str_message_id(self) -> str:
        return str(self.message_id)

    def str_group_id(self) -> str:
        return str(self.group_id)

    def str_sender_id(self) -> str:
        return str(self.sender_id)

    # def str_reply_message_id(self) -> str | None:
    #     return trans_str(self.reply_message_id)

    def str_at_user_id(self) -> str | None:
        return str(self.at_user_id) if self.at_user_id else None

    @classmethod
    async def from_group_message(
        cls, data: GroupMessage, from_bot: bool, api: BotAPI | None = None
    ) -> "GroupMessageRecord":
        print(data)
        def get_data_from_message(message: list[dict]) -> tuple[str,int|None]:
            # return next(
            #     (item["data"] for item in message if item.get("type") == type),
            #     {},
            # )
            contents = []
            at_user_id = None
            for item in message:
                if item.get("type") == "text":
                    contents.append(item.get("data", {}).get("text", ""))
                elif item.get("type") == "image":
                    contents.append("你收到了一张照片，但是你还看不懂照片的内容")
                elif item.get("type") == "record":
                    contents.append("你收到了一段语音，但是你还听不懂语音的内容")
                elif item.get("type") == "face":
                    if face_text := item.get("data", {}).get("raw",{}).get("faceText",""):
                        contents.append(face_text)
                    else:
                        contents.append("你收到了一个表情包，但是你看不懂表情包的意思")
                elif item.get("type") == "at":
                    at_user = item.get("data", {}).get("qq", "")
                    if at_user != "all":
                        at_user_id = int(at_user)


            return "\n".join(contents),at_user_id

        content,at_user_id = get_data_from_message(data.message)
        send_time = time_trans_str(data.time)



        return cls(
            message_id=data.message_id,
            group_id=data.group_id,
            content=content,
            sender_id=data.sender.user_id,
            at_user_id=at_user_id,
            from_bot=from_bot,
            send_time=send_time,
        )


class PrivateMessageRecord(BaseModel):
    message_id: int
    user_id: int
    content: str
    from_bot: bool
    send_time: str

    def str_user_id(self) -> str:
        return str(self.user_id)

    def get_datetime(self) -> datetime:
        return datetime.fromisoformat(self.send_time)

    def str_id(self) -> str:
        return str(self.message_id)


    @classmethod
    async def from_private_message(
            cls, data: PrivateMessage, from_bot: bool, api: BotAPI | None = None
    ) -> "PrivateMessageRecord":
        def get_data_from_message(message: list[dict]) -> str:
            # return next(
            #     (item["data"] for item in message if item.get("type") == type),
            #     {},
            # )
            contents = []
            for item in message:
                if item.get("type") == "text":
                    contents.append(item.get("data", {}).get("text", ""))
                elif item.get("type") == "image":
                    contents.append("你收到了一张照片，但是你还看不懂照片的内容")
                elif item.get("type") == "record":
                    contents.append("你收到了一段语音，但是你还听不懂语音的内容")
                elif item.get("type") == "face":
                    if face_text := item.get("data", {}).get("raw",{}).get("faceText",""):
                        contents.append(face_text)
                    else:
                        contents.append("你收到了一个表情包，但是你看不懂表情包的意思")
            return "\n".join(contents)


        content = get_data_from_message(data.message).strip()
        send_time = time_trans_str(data.time)

        return cls(
            message_id=data.message_id,
            user_id=data.user_id,
            content=content,
            from_bot=from_bot,
            send_time=send_time,
        )


class EntityObject(BaseModel):
    id: str
    name: str
    attribute: str
    real_id: str  # 对于QQ用户实体，real id为QQ id

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, EntityObject) and self.id == other.id


class RelationObject(BaseModel):
    id: str
    name: str
    describe: str


class RelationTriplet(BaseModel):
    subject: EntityObject
    object: EntityObject
    relation: RelationObject
