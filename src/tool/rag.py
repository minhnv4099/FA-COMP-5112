#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import Any

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS

from src.registry import RegisterTool
from src.tool.base import BaseToolSchema
from src.tool.schema import QueryRetrieveArgsSchema
from src.tool.base import BaseDefinedTool

logger = logging.getLogger(__name__)


@RegisterTool(module_path=__name__, name='retrieve_query')
class QueryRetriever(BaseDefinedTool):
    """"""

    name: str = 'retrieve_query'

    description: str = """This tool is called when need to retrieve documents based on query"""

    args_schema: type[BaseToolSchema] = QueryRetrieveArgsSchema

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        assert 'embedding_name' in kwargs
        self.embedding_name = kwargs['embedding_name']
        assert 'db_path' in kwargs
        self.db_path = kwargs['db_path']

        # TODO: consider other model
        gpt4all_kwargs = {'allow_download': 'True'}
        self.embedding = GPT4AllEmbeddings(
            model_name=kwargs['embedding_name'],
            gpt4all_kwargs=gpt4all_kwargs,
            client=None
        )

        logger.info(f'Load vectorstore in "{self.db_path}"')
        # TODO: consider other db
        self.db = FAISS.load_local(
            folder_path=self.db_path,
            embeddings=self.embedding,
            allow_dangerous_deserialization=True,
        )
        self.retrieving_engine = self.db.as_retriever(
            search_type='similarity',
            search_kwargs={
                'k': kwargs.get('n_docs', 4),
            },
        )

    def _run(self, query: str, *args: Any, **kwargs: Any) -> Any:
        docs = self.retrieving_engine.invoke(query)

        return "\n\n".join(self.normalize_urls(doc.page_content) for doc in docs)

    def normalize_urls(self, text: str):
        import re
        url_pattern = re.compile(
            r"(https?://[a-zA-Z0-9/:?&=+.%#_\-\n]+)",
        )

        def fix(match):
            return match.group(1).replace("\n", "").replace(" ", "")

        cleaned = url_pattern.sub(fix, text)

        return cleaned
