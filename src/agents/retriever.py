#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from typing_extensions import override

from src.base.agent import AgentAsNode


class RetrieverAgent(AgentAsNode, name="Retriever"):
    """
    The Retriever Agent class
    """

    def __init__(
            self,
            metadata: dict = None,
            input_schema: Any = None,
            edges: dict[str, tuple[str]] = None,
            tool_schemas: list = None,
            output_schema: Any = None,
            db_path: str = None,
            embedding_name: str = None,
            **kwargs
    ):
        super().__init__(
            metadata=metadata,
            input_schema=input_schema,
            edges=edges,
            tool_schemas=tool_schemas,
            output_schema=output_schema,
        )

        gpt4all_kwargs = {'allow_download': 'True'}
        self.embedding = GPT4AllEmbeddings(
            model_name=embedding_name,
            gpt4all_kwargs=gpt4all_kwargs,
            client=None
        )

        self.db_path = db_path
        self.db = FAISS.load_local(
            self.db_path,
            embeddings=self.embedding,
            allow_dangerous_deserialization=True,
        )
        self.retrieving_engine = self.db.as_retriever(
            search_type='similarity',
            search_kwargs={'k': 1}
        )

    def validate_retrieving(self):
        """Validate retrieving settings"""

    @override
    def validate_model(self, llm_kwargs: dict):
        raise NotImplementedError

    @override
    def __call__(self, state, **kwargs):
        task_docs = dict()
        for i, subtask in enumerate(state['subtasks']):
            docs: Document = self.retrieving_engine.invoke(subtask)[-1]
            docs = docs.page_content
            task_docs[i] = (subtask, docs)

        return task_docs
