import os
from datetime import datetime
from ncatbot.core import BotAPI, BotClient, GroupMessage, PrivateMessage
from PIL import Image
from datetime import datetime
from ncatbot.plugin import BasePlugin

from qq_bot.core.agent.base import AgentBase
from qq_bot.utils.decorator import MessageCommands
from qq_bot.utils.models import GroupMessageRecord, PrivateMessageRecord
from qq_bot.utils.util import blue_image
from qq_bot.core.agent.agent_server import group_random_chat
from qq_bot.core import random_pic_provider
from qq_bot.conn.minio.base import minio
from qq_bot.utils.config import settings
from qq_bot.utils.logging import logger


@MessageCommands(command=f"{settings.BOT_COMMAND_GROUP_RANDOM_PIC}")
async def group_random_picture(
    agent: AgentBase, message: GroupMessageRecord, **kwargs
) -> bool:
    logger.info(f"[{message.id}] 随机图片命令触发")

    local_file, url = random_pic_provider.load()
    if local_file:
        remote_file = os.path.join(
            datetime.now().strftime("%Y-%m"), os.path.basename(local_file)
        )
        minio.upload_files(
            bucket=settings.MINIO_RANDOM_PIC_BOCKET_NAME,
            upload_file={local_file: remote_file},
        )

        await agent.api.post_group_msg(message.group_id, image=url)
        os.remove(local_file)
    return True


@MessageCommands(command=f"{settings.BOT_COMMAND_GROUP_RANDOM_SETU}")
async def group_random_setu(
    agent: AgentBase, message: GroupMessageRecord, **kwargs
) -> bool:
    logger.info(f"[{message.id}] 随机setu命令触发")

    num = 1

    logger.info(f"[SETU]: GROUP {message.group_id} -> 准备发送{num}张")
    for local_file_origin, url in random_pic_provider.load_r18(num=num):
        if local_file_origin and url:
            local_time = datetime.now().strftime("%Y-%m")
            remote_file_origin = os.path.join(
                local_time, "origin", os.path.basename(local_file_origin)
            )

            local_file_processed = f"{'.'.join(local_file_origin.split('.')[:-1])}_processed.{local_file_origin.split('.')[-1]}"

            blue_image(Image.open(local_file_origin)).save(local_file_processed)

            minio.upload_files(
                bucket=settings.MINIO_RANDOM_PIC_BOCKET_NAME,
                upload_file={local_file_origin: remote_file_origin},
            )
            bastion_message = await agent.api.post_group_msg(
                group_id=message.group_id, image=local_file_processed
            )

            if bastion_message["status"] == "ok":
                logger.info(
                    f"[SETU]: GROUP {message.group_id} -> {local_file_origin} 已发送"
                )
            else:
                logger.warning(
                    f"[SETU]: GROUP {message.group_id} -> {local_file_origin} 发送失败"
                )

            os.remove(local_file_origin)
            os.remove(local_file_processed)

    return True


@MessageCommands(command=f"{settings.BOT_COMMAND_GROUP_TOOL}", need_at=True)
async def group_use_tool(agent: AgentBase, message: GroupMessageRecord, **kwargs) -> bool:
    status = await agent.tools.run(message=message)
    if status:
        logger.info(f"[{message.id}] 工具调用触发")

    return status


@MessageCommands(command=f"{settings.BOT_COMMAND_GROUP_REPLY}", need_at=True)
async def group_at_reply(agent: AgentBase, message: GroupMessageRecord, **kwargs) -> bool:
    status = await group_random_chat(
        api=agent.api, message=message, prob=1.0, need_split=True
    )
    if status:
        logger.info(f"[{message.id}] AT回复触发")


@MessageCommands(command=f"{settings.BOT_COMMAND_GROUP_CHAT}")
async def group_at_chat(agent: AgentBase, message: GroupMessageRecord, **kwargs) -> bool:
    status = await group_random_chat(
        api=agent.api,
        message=message,
        prob=settings.CHAT_WILLINGNESS,
        need_split=True,
    )
    if status:
        logger.info(f"[{message.id}] 随机聊天触发")




@MessageCommands(command=f"{settings.BOT_COMMAND_PRIVATE_DIARY}")
async def private_diary_record(agent: BasePlugin, message: PrivateMessageRecord, **kwargs) -> bool:
    try:
        now = datetime.now()
        date_str = now.strftime("%Y-%m-%d")
        month_str = now.strftime("%Y-%m")
        diary_dir = os.path.join(settings.DIARY_PATH, "diary_record", str(message.user_id), month_str)
        if diary_dir and not os.path.exists(diary_dir):
            os.makedirs(diary_dir)
        diary_path = os.path.join(diary_dir, f"diary_{date_str}.txt")

        cleaned_text = message.content.replace("#今日日记", "", 1)

        with open(diary_path, 'w', encoding='utf-8') as file:
            file.write(cleaned_text.strip())
            await agent.api.post_private_msg(user_id=message.user_id,text="日记保存成功")
        return True
    except:
        await agent.api.post_private_msg(user_id=message.user_id,text="日记保存失败")
        return False
