import asyncio
from datetime import datetime
import functools
import importlib
import inspect
import json
import os
import pkgutil
import re
from typing import Literal
import requests
import json
import yaml
from PIL import Image
from ncatbot.core import GroupMessage
from qq_bot.utils.logging import logger
import requests
import json


def load_yaml(yaml_path: str) -> dict:
    try:
        with open(yaml_path) as yaml_file:
            return yaml.safe_load(yaml_file)
    except Exception as err:
        logger.error(
            f"[YAML Reader] Error occured when read YAML from path '{yaml_path}'. Error: {err}"
        )
        return {}


def import_all_modules_from_package(package):
    """自动导入指定包中的所有模块

    Args:
        package (_type_): 包名
    """
    for importer, modname, ispkg in pkgutil.walk_packages(
        package.__path__, package.__name__ + "."
    ):
        importlib.import_module(modname)


def stitched_images(images: list[Image.Image]) -> Image.Image | None:
    if len(images) > 0:
        width = 1024

        new_images = []
        for image in images:
            w, h = image.size
            new_images.append(image.resize((width, int(h * width / w)), Image.LANCZOS))

        # width, _ = images[0].size
        mode = new_images[0].mode
        height = sum(i.size[1] for i in new_images)

        result = Image.new(mode=mode, size=(width, height))

        current_height = 0
        for i, image in enumerate(new_images):
            result.paste(image, box=(0, current_height))
            current_height += image.size[1]
        return result


def blue_image(image: Image.Image) -> Image.Image:
    from PIL import ImageFilter

    return image.filter(ImageFilter.BLUR)


def search_meme(keyword: str,
                page: int = 1,
                num: int = 10,
                timeout: int = 5) -> list[str]:

    url = "https://h5api.sginput.qq.com/wxbq/search"
    params = {
        "key": keyword,
        "page": page,
        "num": num
    }
    try:
        resp = requests.post(url, params=params, timeout=timeout)
        resp.raise_for_status()
        result = resp.json()
        meme_urls = [item['indexUrl'].strip() for item in result['data']]
        return meme_urls
    except requests.RequestException as e:
        logger.error("网络或 HTTP 异常：", e)
        return []
    except json.JSONDecodeError as e:
        logger.error("返回内容不是合法 JSON：", e)
        return []