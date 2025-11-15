#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#

# No longer needed
SUPPORTED_LOCAL_MODEL: list = [
    "deepseek-r1:1.5b",
    "gemma3:1b"
]

PROVIDER_TO_ENV: dict[str, str] = {
    None: "OPENROUTER_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
}

PROVIDER_TO_BASE_URL: dict[str, str] = {
    None: "https://openrouter.ai/api/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None,
}
