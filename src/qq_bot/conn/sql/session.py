from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Session, create_engine, select
from sqlmodel.ext.asyncio.session import AsyncSession
from qq_bot.utils.logging import logger
from qq_bot.utils.config import settings
from qq_bot.conn.sql.models import *


from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

local_engine_sync = create_engine(
    url=settings.SQL_DATABASE_URI,
    pool_pre_ping=True,
    echo=settings.DEBUG
)
LocalSessionSync = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=local_engine_sync,
    class_=Session
)

local_engine_async = create_async_engine(
    url=settings.SQL_DATABASE_URI.replace("mysql+pymysql", "mysql+asyncmy"),
    pool_pre_ping=True,
    echo=settings.DEBUG
)
LocalSessionAsync = async_sessionmaker(

    autocommit=False,
    autoflush=False,
    bind=local_engine_async,
    class_=AsyncSession,  # 确保这里使用的是 AsyncSession
    expire_on_commit=False  # 添加这个设置

)


async def get_local_db_async():
    async with LocalSessionAsync() as session:
        yield session


def get_local_db_sync():
    with LocalSessionSync() as session:
        yield session


logger.info(f"[init] Checking database consistency...")
SQLModel.metadata.create_all(local_engine_sync)

# with LocalSession() as db:
#     logger.info(f"[init] Checking message type data consistency...")