#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Any, Literal, Union

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from typing_extensions import override

from src.base.agent import AgentAsNode, register
from src.base.typing import InputT
from src.base.utils import DirectionRouter

logging.getLogger(__name__)


@register(type="agent", name='retriever')
class RetrieverAgent(AgentAsNode, name="Retriever", use_model=False):
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
    def validate_model(self):
        raise NotImplementedError

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: Runtime[RunnableConfig] = None,
            context: Runtime[RunnableConfig] = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Union[dict, Command[Literal['coding']], Send]:
        # logging.info(f"retrieve \n\t{state}")
        retrieved_docs: dict[int, list] = dict()
        for i, query in enumerate(state['queries']):
            docs = self.retrieving_engine.invoke(query)
            retrieved_docs[i] = [doc.page_content for doc in docs]

        update_state = {
            'caller': 'retriever',
            'has_docs': True,
            'is_sub_call': True,
            'coding_task': state['coding_task'],
            'queries': state['queries'],
            'retrieved_docs': retrieved_docs,
            "messages":
                {'role': f"assistant",
                 "content": f"Retriever Agent result documents when '{state['coding_task']}'"}
        }
        # return update_state
        return DirectionRouter.go_next(
            method='command',
            state=update_state,
            node='coding'
        )

    @override
    def chat_model_call(self, query, *args, **kwargs):
        docs = self.retrieving_engine.invoke(query)
