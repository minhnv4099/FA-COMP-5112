#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import Any, TYPE_CHECKING, Type
from typing_extensions import override
from pydantic import BaseModel, Field

from langchain_community.vectorstores import FAISS

from src.tools.base import BaseTool
from src.registry import RegisterTool
from src.telemetry.telemetry_decorator import telemetry_langchain_tool
from src.utils.embeddings import load_openai_embeddings, load_gpt4all_embeddings
from src.utils.exception import ToolCreationError

if TYPE_CHECKING:
    from langchain_community.docstore.document import Document

logger = logging.getLogger(__name__)


class QueryRetrieveArgsSchema(BaseModel):
    """Input for query-retrieving tool."""

    query: str = Field(
        ...,
        description="Query need to retrieve relevant documents from vector store."
    )


@RegisterTool(module=__name__, name='query_retrieve')
class QueryRetrieveTool(BaseTool):
    """"""

    name: str = 'query_retrieve'
    description: str = (
        "A tool is called when need to retrieve documents based on query. "
    )
    args_schema: Type[BaseModel] = QueryRetrieveArgsSchema

    def __init__(
        self,
        db_path: str = None,
        embedding_name: str = None,
        **kwargs: Any
    ):
        super().__init__(**kwargs)

        self.doc_dir: str | None = kwargs.get('doc_dir', None)

        if not (db_path and embedding_name):
            raise ToolCreationError(
                f"You must provide 'db_path' and 'embedding_name', but got {db_path!r} and {embedding_name!r}. "
                f"Ensure embedding name match that used when building vector database "
                f"because we cannot verify it."
            )

        # TODO: consider other models
        if 'openai' in embedding_name:
            embeddings = load_openai_embeddings()
        else:
            embeddings = load_gpt4all_embeddings()

        # TODO: consider other db
        # TODO: add utils to load db
        self.db = FAISS.load_local(
            folder_path=db_path,
            embeddings=embeddings,
            allow_dangerous_deserialization=True,
        )
        self.retrieving_engine = self.db.as_retriever(
            search_type='similarity',
            search_kwargs={
                'k': kwargs.get('n_docs', 4),
            },
        )

    @telemetry_langchain_tool("query_retrieve")
    @override
    def _run(self, query: str) -> Any:
        docs = self.retrieving_engine.invoke(query)
        contents = [self.process_doc(doc) for doc in docs]
        contents = [self.normalize_urls(content) for content in contents]

        return f"\n\n{'='*100}\n".join(contents)

    def process_doc(self, doc: Document) -> str:
        source: str = doc.metadata['source']

        content = f"URI: {source}\n\n"
        content += doc.page_content

        return content

    def normalize_urls(self, text: str):
        import re
        url_pattern = re.compile(
            r"(https?://[a-zA-Z0-9/:?&=+.%#_\-\n]+)",
        )

        def fix(match):
            return match.group(1).replace("\n", "").replace(" ", "")

        cleaned = url_pattern.sub(fix, text)

        return cleaned
