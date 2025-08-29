import json
import random
import re
from typing import Literal
from datetime import datetime, timezone
from qq_bot.utils.logging import logger


def get_data_from_message(message: list[dict], type: str) -> dict:
    return next((item["data"] for item in message if item.get("type") == type), {})


def extract_json_from_markdown(text: str) -> list[dict | list]:
    results = []
    pattern = r"```json\s*([\s\S]*?)\s*```"
    matches = re.findall(pattern, text)
    for index, match in enumerate(matches):
        try:
            parsed = json.loads(match)
            results.append(parsed)
        except Exception as err:
            logger.warning(f"文本段中第{index + 1}个JSON解析失败! 文本: {text}")
            continue
    return results


def parse_text(text):
    lines = text.split("\n")
    count = 0
    for i, line in enumerate(lines):
        if "```" in line:
            count += 1
            items = line.split("`")
            if count % 2 == 1:
                lines[i] = f'<pre><code class="{items[-1]}">'
            else:
                lines[i] = f"</code></pre>"
        else:
            if i > 0:
                if count % 2 == 1:
                    line = line.replace("&", "&amp;")
                    line = line.replace('"', "&quot;")
                    line = line.replace("'", "&apos;")
                    line = line.replace("<", "&lt;")
                    line = line.replace(">", "&gt;")
                    line = line.replace(" ", "&nbsp;")
                lines[i] = "<br/>" + line
    return "".join(lines)


def language_classifity(sentence: str) -> Literal["zh", "en"]:
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", sentence)
    english_chars = re.findall(r"[a-zA-Z]", sentence)

    if len(chinese_chars) > len(english_chars):
        return "zh"
    elif len(english_chars) > len(chinese_chars):
        return "en"


def split_sentence_zh(text: str) -> list[str]:
    text = text.strip()
    text = re.sub(r"([。！？~～?.])([^”’])", r"\1\n\2", text)
    text = re.sub(r"([\.。]{2,}|…{2,})([^”’])", r"\1\n\2", text)
    text = re.sub(r"([。！？~～?.][”’])([^，。！？?.])", r"\1\n\2", text)

    return [line.strip() for line in text.split("\n") if line.strip()]


def split_sentence_en(text: str) -> list[str]:
    text = text.strip()
    text = re.sub(r"([.!?])(\s+)([A-Z])", r"\1\n\3", text)
    text = text.strip()
    return [line.strip() for line in text.split("\n") if line.strip()]


def auto_split_sentence(
    text: str, language: Literal["zh", "en", None] = None
) -> list[str]:
    language = language if language else language_classifity(text)
    if language == "zh":
        return split_sentence_zh(text)
    else:
        return split_sentence_en(text)


def typing_time_calculate(text: str, language: Literal["zh", "en", None] = None) -> float:
    language = language if language else language_classifity(text)
    typing_time = len(text) / 3.0 / (5.0 if language == "en" else 1.0)
    return typing_time + random.random()


def trans_int(data: int | str | None) -> int | None:
    return int(data) if data else None


def trans_str(data: int | str | None) -> str | None:
    return str(data) if data else None


def time_trans_str(ts: int)->str:
    return datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')

def time_trans_int(dt_str: str)->int:
    return int(datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').replace().timestamp())

