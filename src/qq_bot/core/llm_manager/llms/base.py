import os
import json
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
from ncatbot.plugin import BasePlugin

from qq_bot.core.tool_manager.tool_registrar import ToolRegistrar
from qq_bot.utils.util import load_yaml
from qq_bot.utils.decorator import function_retry
from qq_bot.core.mcp_manager.mcp_register import get_mcp_register

from qq_bot.utils.config import settings

class OpenAIBase:
    __model_tag__ = "openai"
    _subclasses = []

    def __init__(
        self,
        base_url: str,
        api_key: str,
        prompt_path: str,
        bot: BasePlugin,
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
        self.bot = bot

    async def init(self):
        self.mcp_tools = await get_mcp_register() if settings.MCP_ACTIVATE else None
        self.local_tools = ToolRegistrar(agent=self.bot)
        self.tool_description = [*self.mcp_tools.tools_description, *self.local_tools.tool_dec]

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
            print(completion)
            if completion.choices and completion.choices[-1].message:
                raw = completion.choices[-1].message.content or ""
                cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                completion.choices[-1].message.content = cleaned
                return completion.choices[-1].message

            return None
        else:
            return self.default_reply





    @function_retry
    async def _async_tool_inference(
            self,
            user_id: int,
            content: Any,
            model: Optional[str] = None,
            **kwargs
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

            iterations = 0
            max_iterations=5
            while iterations < max_iterations:  # 防止无限循环
                iterations += 1
                completion = await self.async_client.chat.completions.create(
                    messages=messages, model=model, tools=self.tool_description, **kwargs
                )
                if completion.choices and completion.choices[-1].message:
                    raw = completion.choices[-1].message.content or ""
                    cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
                    completion.choices[-1].message.content = cleaned
                    llm_message = completion.choices[-1].message

                    if llm_message and llm_message.tool_calls:
                        messages.append({
                            "role": "assistant",
                            "content": llm_message.content or "",
                            "tool_calls": [
                                {
                                    "id": tc.id,
                                    "type": "function",
                                    "function": {
                                        "name": tc.function.name,
                                        "arguments": tc.function.arguments
                                    }
                                } for tc in llm_message.tool_calls
                            ]
                        })


                        for tool_call in llm_message.tool_calls:
                            tool_name = tool_call.function.name
                            args = json.loads(tool_call.function.arguments)
                            if tool_name in self.mcp_tools.tools:
                                res = await self.mcp_tools.execute_tool(tool_name,args)
                                messages.append({"content":str(res),"role":"tool","tool_call_id": tool_call.id})
                            elif tool_name in self.local_tools.tools:
                                res = await self.local_tools.run(tool_name,**{**args,"user_id":user_id})
                                messages.append({"content":str(res),"role":"tool","tool_call_id": tool_call.id})
                    else:
                        return completion.choices[-1].message
                else:
                    return self.default_reply
            return self.default_reply








        #     first_completion = await self.async_client.chat.completions.create(
        #         messages=messages, model=model, tools=self.mcp_tools.tools_description,**kwargs
        #     )
        #     print("第一次对话",first_completion)
        #     if first_completion.choices and first_completion.choices[-1].message:
        #         raw = first_completion.choices[-1].message.content or ""
        #         cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        #         first_completion.choices[-1].message.content = cleaned
        #         llm_message = first_completion.choices[-1].message
        #
        #         if llm_message and llm_message.tool_calls:
        #             tool_call = llm_message.tool_calls[0]
        #             tool_name = tool_call.function.name
        #             args = json.loads(tool_call.function.arguments)
        #             if tool_name in self.mcp_tools.tools:
        #                 res = await self.mcp_tools.execute_tool(tool_name,args)
        #                 print("工具调用",res)
        #
        #                 messages.insert(-1, {"content":res,"role":"assistant"})
        #         else:
        #             return first_completion.choices[-1].message
        #     print(type(messages),messages)
        #     second_completion = await self.async_client.chat.completions.create(
        #         messages=messages, model=model, tools=self.mcp_tools.tools_description, **kwargs
        #     )
        #     print("第二次对话",second_completion)
        #     if second_completion.choices and second_completion.choices[-1].message:
        #         raw = second_completion.choices[-1].message.content or ""
        #         cleaned = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        #         second_completion.choices[-1].message.content = cleaned
        #         return second_completion.choices[-1].message
        #     return None
        # else:
        #     return self.default_reply


    # @function_retry
    # async def _async_execute_tool(
    #         self, function_name: str, **kwargs
    # ) -> str| None:


    async def run(self, message: Any, **kwargs) -> Any:
        pass
