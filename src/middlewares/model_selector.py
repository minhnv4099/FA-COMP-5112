#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations
import logging
import os
from typing import Callable, Awaitable
from langchain.agents.middleware import wrap_model_call, AgentMiddleware
from langchain.agents.middleware.types import ModelRequest, ModelResponse, AgentState, ModelCallResult
from langchain.chat_models import BaseChatModel, init_chat_model


logger = logging.getLogger('ModelSelector')
available_models: dict[str, BaseChatModel] | None = None

#
#  Copyright (c) 2026
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
REASONING_FLAGS = {
    'deepseek': ('<think>', '</think>'),
    None: ('<reasoning>', '</reasoning>')
}

OPENROUTER_SUPPORTED_MODELS = {
    'Default': None,
    'NVIDIA: Nemotron Nano 12B 2 VL (free)': 'nvidia/nemotron-nano-12b-v2-vl:free',  # ok
    'NVIDIA: Nemotron 3 Nano 30B A3B (free)': 'nvidia/nemotron-3-nano-30b-a3b:free',  # ok
    'NVIDIA: Nemotron 3 Super (free)': 'nvidia/nemotron-3-super-120b-a12b:free',  #
    'Qwen: Qwen3.6 Plus Preview (free)': "qwen/qwen3.6-plus-preview:free",  # ok
    'StepFun: Step 3.5 Flash (free)': 'stepfun/step-3.5-flash:free'
    # 'MiniMax: MiniMax M2.5 (free)': 'minimax/minimax-m2.5:free',
    # 'OpenAI: gpt-oss-120b (free)': 'openai/gpt-oss-120b:free',  # not work
    # 'OpenAI: gpt-oss-20b (free)': 'openai/gpt-oss-20b:free' # not work
}

HUGGINGFACE_SUPPORTED_MODEL = {
    'DeepSeek-R1': 'deepseek-ai/DeepSeek-R1',  # ok
    'DeepSeek-R1-0528': 'deepseek-ai/DeepSeek-R1-0528',  # ok
    # 'DeepSeek-R1-Distill-Llama-8B': 'deepseek-ai/DeepSeek-R1-Distill-Llama-8B:nscale', # no ok
    # 'DeepSeek-V3': 'deepseek-ai/DeepSeek-V3',
    # 'DeepSeek-V3-0324': 'deepseek-ai/DeepSeek-V3-0324:novita',
}


def get_available_model(model_name: str):
    global available_models
    if available_models is None:
        available_models = {}

    if model_name not in available_models:
        if model_name not in OPENROUTER_SUPPORTED_MODELS:
            logger.error(f'{model_name!r} is not in supported models: {list(OPENROUTER_SUPPORTED_MODELS.keys())}')
        else:
            model_id = OPENROUTER_SUPPORTED_MODELS[model_name]
            if model_id:
                model_id = 'openrouter:' + model_id
                available_models[model_name] = init_chat_model(
                    model=model_id,
                    base_url=os.getenv('BASE_URL'),
                    api_key=os.getenv('OPENROUTER_API_KEY'),
                    name=model_id,
                )

    return available_models.get(model_name)


class ModelSelector(AgentMiddleware):
    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelCallResult:
        override_model = None
        if context := request.runtime.context:
            model_name = context.get('model_name')
            override_model = get_available_model(model_name)

        if override_model is not None:
            request = request.override(model=override_model)

        logger.info(f'Thinking by {request.model.name!r}.')

        return await handler(request)
