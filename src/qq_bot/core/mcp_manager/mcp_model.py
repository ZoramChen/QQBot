from pydantic import BaseModel, PrivateAttr
from typing import Any
import re
# 今日头条 抖音
def toutiao_trending_to_str(raw_data: Any)->str:
    if not raw_data:
        return ""
    parts = []
    for index,item in enumerate(raw_data[:10],start=1):
        title = re.search(r'<title>(.*?)</title>', item.text).group(1)
        popularity = re.search(r'<popularity>(\d+)</popularity>', item.text).group(1)
        link = re.search(r'<link>(.*?)</link>', item.text).group(1)
        parts.append(f"标题：{title} 热度：{popularity} 链接：{link}")
    return "\n".join(parts)
#哔哩哔哩
def bilibili_trending_to_str(raw_data: Any)->str:
    if not raw_data:
        return ""
    parts = []
    for index,item in enumerate(raw_data[:10],start=1):
        title = re.search(r'<title>(.*?)</title>', item.text).group(1)
        link = re.search(r'<link>(.*?)</link>', item.text).group(1)
        parts.append(f"标题：{title} 链接：{link}")
    return "\n".join(parts)


mcp_model_dict = {
    "get-bilibili-rank": bilibili_trending_to_str,
    "get-douyin-trending":toutiao_trending_to_str,
    "get-toutiao-trending": toutiao_trending_to_str,
}