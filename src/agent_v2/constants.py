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
    # 'MiniMax: MiniMax M2.5 (free)': 'minimax/minimax-m2.5:free',
    'NVIDIA: Nemotron Nano 12B 2 VL (free)': 'nvidia/nemotron-nano-12b-v2-vl:free',  # ok
    'NVIDIA: Nemotron 3 Nano 30B A3B (free)': 'nvidia/nemotron-3-nano-30b-a3b:free',  # ok
    'NVIDIA: Nemotron 3 Super (free)': 'nvidia/nemotron-3-super-120b-a12b:free',  #
    'Qwen: Qwen3.6 Plus Preview (free)': "qwen/qwen3.6-plus-preview:free",  # ok
    'StepFun: Step 3.5 Flash (free)': 'stepfun/step-3.5-flash:free'
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
