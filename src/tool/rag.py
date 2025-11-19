#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS

from src.registry import RegisterTool
from src.tool.base import BaseToolSchema
from src.tool.schema import QueryRetrieveArgsSchema
from src.tool.base import BaseDefinedTool

if TYPE_CHECKING:
    from langchain_community.docstore.document import Document

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
        self.embedding_name: str = kwargs['embedding_name']
        assert 'db_path' in kwargs
        self.db_path: str = kwargs['db_path']
        self.doc_dir: str | None = kwargs.get('doc_dir', None)

        # TODO: consider other model
        # TODO: add utils to load embedding models
        gpt4all_kwargs = {'allow_download': 'True'}
        # NOTE: use
        self.embedding = GPT4AllEmbeddings(
            model_name=kwargs['embedding_name'],
            gpt4all_kwargs=gpt4all_kwargs,
            client=None
        )

        logger.info(f'Load vectorstore in "{self.db_path}"')
        # TODO: consider other db
        # TODO: add utils to load db
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

        contents = [self.process_doc(doc) for doc in docs]
        contents = [self.normalize_urls(content) for content in contents]

        return f"\n\n{'='*100}\n".join(contents)

    def normalize_urls(self, text: str):
        import re
        url_pattern = re.compile(
            r"(https?://[a-zA-Z0-9/:?&=+.%#_\-\n]+)",
        )

        def fix(match):
            return match.group(1).replace("\n", "").replace(" ", "")

        cleaned = url_pattern.sub(fix, text)

        return cleaned

    def process_doc(self, doc: Document) -> str:
        import os

        file: str = doc.metadata['source']
        if self.doc_dir:
            url = file.replace(self.doc_dir, 'https://')
        else:
            url = file

        if 'can_remove_index' in file:
            # process index url
            url = os.path.split(url)[0]
        else:
            url = url[:url.rfind('/')] + '?' + url[url.rfind('/'):]
            url = os.path.splitext(url)[0]

        content = f"LINK: {url}\n\n"
        content += doc.page_content

        return content
