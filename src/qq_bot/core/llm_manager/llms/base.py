import os
import re
from functools import partial
from typing import Any, Optional, Union
from openai import AsyncOpenAI, OpenAI
from openai.types.chat import (
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionMessage,
)
from qq_bot.utils.util import load_yaml
from qq_bot.utils.decorator import function_retry


class OpenAIBase:
    __model_tag__ = "openai"
    _subclasses = []

    def __init__(
        self,
        base_url: str,
        api_key: str,
        prompt_path: str,
        max_retries: int = 3,
        retry: int = 3,
        **kwargs,
    ) -> None:
        # assert os.path.isfile(prompt_path)

        self.retry = retry
        self.configs: dict = load_yaml(prompt_path)
        self._load_config()

        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=20,
            **kwargs,
        )
        self.async_client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            max_retries=max_retries,
            timeout=20,
            **kwargs,
        )

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        OpenAIBase._subclasses.append(cls)

    @classmethod
    def subclasses(cls):
        return cls._subclasses

    def _load_config(self):
        prompt_version = self.configs.get("version", "v1")

        self.default_model = self.configs.get("model", "gpt-3.5-turbo-ca")
        self.is_activate: bool = self.configs.get("activate", False)
        self.default_reply: str = self.configs.get("default_reply", "None")
        self.prompt: str = self.configs.get("prompts", {}).get(prompt_version, "")
        self.custom_system_prompt: str = self.configs.get("custom_system_prompt", {}).get(prompt_version, "")
        self.base_system_prompt = ChatCompletionSystemMessageParam(
            content=(
                self.configs.get("base_system_prompt", {}).get(
                    prompt_version, "You are a helpful assistant."
                )
            ),
            role="system",
        )

    def _set_prompt(self, input: dict, prompt: str | None = None) -> str:
        def replacer(match, params: dict):
            var_name = match.group(1)
            return params.get(var_name, match.group(0))

        def standardization(params: Union[dict, str]) -> dict:
            params = {"data": params} if isinstance(input, str) else input
            return {k: str(v) for k, v in params.items()}

        params = standardization(input)
        pattern = re.compile(r"\$\{(\w+)\}")
        prompt = prompt if prompt else self.prompt
        return pattern.sub(partial(replacer, params=params), prompt)

    def format_user_message(
        self, content: str, **kwargs
    ) -> ChatCompletionUserMessageParam:
        return ChatCompletionUserMessageParam(content=content, role="user", **kwargs)

    def format_llm_message(self, content: str) -> ChatCompletionAssistantMessageParam:
        return ChatCompletionAssistantMessageParam(content=content, role="assistant")

    def _inference(self, content: str, model: Optional[str] = None, **kwargs) -> str:
        if self.is_activate:
            model = model or self.default_model

            if isinstance(content, str):
                messages = [
                    self.base_system_prompt,
                    self.format_user_message(content=content),
                ]
            if isinstance(content, list):
                content.insert(0, self.base_system_prompt)
                messages = content
            completion = self.client.chat.completions.create(
                messages=messages,
                model=model,
                **kwargs,  # type: ignore
            )
            if completion.choices and completion.choices[-1].message:
                response = completion.choices[-1].message.content
                if response:
                    return response
                return None
            return None
        else:
            return self.default_reply

    @function_retry
    async def _async_inference(
        self, content: Any, model: Optional[str] = None, **kwargs
    ) -> ChatCompletionMessage | None:
        if self.is_activate:
            assert isinstance(content, str) or isinstance(
                content, list
            ), f"Illegal LLM input type: {type(content)}"

            model = model or self.default_model
            if isinstance(content, str):
                messages = [
                    self.base_system_prompt,
                    self.format_user_message(content=content),
                ]
            if isinstance(content, list):
                content.insert(0, self.base_system_prompt)
                messages = content
            if "custom_system_prompt" in kwargs:
                if kwargs["custom_system_prompt"]:
                    messages.insert(1, kwargs["custom_system_prompt"])
                kwargs.pop("custom_system_prompt")
            completion = await self.async_client.chat.completions.create(
                messages=messages, model=model, **kwargs
            )
            if completion.choices and completion.choices[-1].message:
                raw = completion.choices[-1].message.content or ""
                cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                completion.choices[-1].message.content = cleaned
                return completion.choices[-1].message

            return None
        else:
            return self.default_reply

    async def run(self, message: Any, **kwargs) -> Any:
        pass
