#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os

from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_huggingface.embeddings import HuggingFaceEmbeddings


def load_openai_embeddings(
    embedding_name: str = 'openai/text-embedding-3-small',
    api_key: str = None,
    base_url: str = None
):
    from src.utils import find_load_env

    find_load_env()

    api_key = api_key if api_key else os.getenv('OPENROUTER_API_KEY')
    base_url = base_url if base_url else os.getenv('BASE_URL')

    embeddings = OpenAIEmbeddings(
        model=embedding_name,
        api_key=api_key,
        base_url=base_url
        # With the `text-embedding-3` class
        # of models, you can specify the size
        # of the embeddings you want returned.
        # dimensions=1024
    )

    return embeddings


def load_gpt4all_embeddings(embedding_name: str = "all-MiniLM-L6-v2.gguf2.f16.gguf"):
    gpt4all_kwargs = {'allow_download': 'True'}
    embeddings = GPT4AllEmbeddings(
        model_name=embedding_name,
        gpt4all_kwargs=gpt4all_kwargs,
        client=None
    )

    return embeddings


def load_huggingface_embeddings(model_name: str = "sentence-transformers/all-mpnet-base-v2"):
    model_kwargs = {'device': 'cpu'}
    encode_kwargs = {'normalize_embeddings': False}

    return HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
