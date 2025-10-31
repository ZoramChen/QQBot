import os
from typing import Optional, Dict
from qq_bot.utils.config import settings
from qq_bot.utils.logging import logger
from qq_bot.core.llm_manager.llms.base import OpenAIBase
import qq_bot.core.llm_manager.llms as bot_llms
from qq_bot.utils.util import import_all_modules_from_package
from ncatbot.plugin import BasePlugin

class LLMRegistrar:
    def __init__(self, prompt_root: str):
        self.prompt_root = prompt_root
        self.model_services: Dict[str, OpenAIBase] = {}

    # ---------- 异步初始化 ----------
    async def async_init(self, bot: BasePlugin) -> "LLMRegistrar":
        await self._load_model_services(bot)
        return self

    # 工厂函数：推荐用法
    @staticmethod
    async def create(prompt_root: str, bot: BasePlugin) -> "LLMRegistrar":
        return await LLMRegistrar(prompt_root).async_init(bot)

    # 真正的异步加载
    async def _load_model_services(self, bot: BasePlugin) -> None:
        import_all_modules_from_package(bot_llms)
        model_services = OpenAIBase.__subclasses__()
        logger.info("正在注册模型服务")
        for model_service in model_services:
            tag = model_service.__model_tag__
            prompt_path = os.path.join(self.prompt_root, f"{tag}.yaml")
            inst = model_service(
                base_url=settings.GPT_BASE_URL,
                api_key=settings.GPT_API_KEY,
                prompt_path=prompt_path,
                bot=bot,
            )
            await inst.init()                      # 异步初始化
            self.model_services[tag] = inst
            logger.info(f"已注册模型：{tag}" if inst.is_activate else
                        f"已注册模型：{tag} [未激活]")

    # 同步获取（初始化完成后才可使用）
    def get(self, model_tag: str) -> Optional[OpenAIBase]:
        return self.model_services.get(model_tag)


# ---------- 模块级异步单例 ----------
_reg: Optional[LLMRegistrar] = None

async def get_llm_registrar(bot: BasePlugin) -> LLMRegistrar:
    global _reg
    if _reg is None:
        _reg = await LLMRegistrar.create(settings.LOCAL_PROMPT_ROOT, bot)
    return _reg
