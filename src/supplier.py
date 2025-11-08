#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#

SUPPORTED_MODEL: list = [
    "gpt-4o-mini",
    "gpt-4o",
]

PROVIDER_TO_ENV: dict[str, str] = {
    None: "OPENROUTER_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY"
}

PROVIDER_TO_BASE_URL: dict[str, str] = {
    None: "https://openrouter.ai/api/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "openai": None
}
