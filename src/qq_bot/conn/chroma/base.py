import chromadb
import openai
from openai import OpenAI
from chromadb.api.models.Collection import Collection
from qq_bot.utils.decorator import sql_session
from typing import List
from sqlmodel import Session, select
from sqlalchemy import asc
from qq_bot.conn.sql.models import PrivateMessageV1
from qq_bot.utils.logging import logger

class ChromaEmbeddingFunction(chromadb.EmbeddingFunction):
    def __init__(self, model_name: str, base_url: str, api_key: str = None):
        self.model_name = model_name
        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)

    def __call__(self, input_texts):
        # 检查 input_texts 是否为列表，如果不是则转换为列表
        if not isinstance(input_texts, list):
            input_texts = [input_texts]

        embeddings = []
        for text in input_texts:
            try:
                response = self.client.embeddings.create(
                    model=self.model_name,
                    input=text,
                )
                embeddings.append(response.data[0].embedding)
            except Exception as e:
                logger.info(f"Embedding 请求出错: {e}")
                return None
        return embeddings


def is_id_exists(collection:Collection, id: str) -> bool:
    """
    检查指定 ID 是否在集合中存在
    """
    try:
        result = collection.get(ids=[id])
        return len(result["ids"]) > 0
    except Exception as e:
        logger.info(f"检查 ID 时出错: {e}")
        return False


def batch_check_ids(collection:Collection, id_list:list[str]):
    try:
        # 获取所有指定 ID 的文档
        result = collection.get(ids=id_list)
        existing_ids = set(result["ids"])

        # 构建与输入顺序一致的结果列表
        status_list = [doc_id in existing_ids for doc_id in id_list]

        return status_list

    except Exception as e:
        logger.info(f"批量检查 ID 时出错: {e}")
        return [False] * len(id_list)


def batch_add(collection:Collection, documents:list[str], ids:list[str], metadata:list|None=None):
    collection.add(
        documents=documents,
        ids=ids,
        metadatas=metadata
    )

def message_add(collection:Collection, document:str, id:str, metadata:dict|None=None):
    collection.add(
        documents=[document],
        ids=[id],
        metadatas=[metadata]
    )

def messages_query(collection:Collection, query_msg:str, conditions:dict=None, msg_num:int = 10)->str:
    results = collection.query(
        query_texts=[query_msg],
        n_results=msg_num,  # 获取前3个最相关的文档
        where=conditions
    )
    return "历史参考对话:\n"+"；".join(results['documents'][0])


