#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Any, Literal, Union

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.runnables import RunnableLambda
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command, Send
from typing_extensions import override

from ..base.agent import AgentAsNode, register
from ..base.utils import DirectionRouter
from ..utils import InputT

logger = logging.getLogger(__name__)


@register(type="agent", name='retriever')
class RetrieverAgent(AgentAsNode, node_name="Retriever", use_model=True):
    """
    The Retriever Agent class
    """

    def __init__(
            self,
            metadata: dict = None,
            edges: dict[str, tuple[str]] = None,
            input_schema: Any = None,
            tool_schemas: list = None,
            output_schema: Any = None,
            embedding_name: str = None,
            n_docs: int = None,
            db_path: str = None,
            template_file: str = None,
            **kwargs
    ):
        super().__init__(
            metadata=metadata,
            edges=edges,
            input_schema=input_schema,
            tool_schemas=tool_schemas,
            output_schema=output_schema,
            template_file=template_file,
            **kwargs,
        )
        super()._prepare_chat_template()

        gpt4all_kwargs = {'allow_download': 'True'}
        self.embedding = GPT4AllEmbeddings(
            model_name=embedding_name,
            gpt4all_kwargs=gpt4all_kwargs,
            client=None
        )

        logger.info('Load vectorstore')
        self.db_path = db_path
        self.db = FAISS.load_local(
            self.db_path,
            embeddings=self.embedding,
            allow_dangerous_deserialization=True,
        )
        self.retrieving_engine = self.db.as_retriever(
            search_type='similarity',
            search_kwargs={'k': n_docs}
        )

        self.chain = RunnableLambda(self._retrieve) | self.chat_template | self.chat_model

    def validate_retrieving(self):
        """Validate retrieving settings"""

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: Runtime[RunnableConfig] = None,
            context: Runtime[RunnableConfig] = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Union[dict, Command[Literal['coding']], Send]:
        start_message = "-" * 50 + self.name + "-" * 50
        logger.info(start_message)
        messages = []
        retrieved_docs: dict[int, list] = dict()
        for i, query in enumerate(state['queries']):
            # -------------------------------------------------
            docs = self.retrieving_engine.invoke(query)
            docs_content = [doc.page_content for doc in docs]
            metadata_docs = [doc.metadata for doc in docs]
            logger.info(f"query {i + 1}/{len(state['queries'])}: {query}")
            logger.info(f"docs metadata: {metadata_docs}")

            formatted_template = self.chat_template.invoke({'query': query, 'retrieved_docs': docs})

            summary, query_messages = self.chat_model_call(formatted_template)
            # -------------------------------------------------
            retrieved_docs[i] = summary
            if messages:
                messages.extend(query_messages[1:])
            else:
                messages.extend(query_messages)

        update_state = {
            'coding_task': state['coding_task'],
            'queries': state['queries'],
            'retrieved_docs': retrieved_docs,
            'caller': 'retriever',
            'is_sub_call': True,
            'has_docs': True,
            "messages": messages
        }

        self.log_conversation(logger, messages)
        end_message = "*" * (100 + len(self.name))
        logger.info(end_message)

        # return update_state
        return DirectionRouter.goto(state=update_state, node='coding', method='command')

    def _retrieve(self, query):
        docs = self.retrieving_engine.invoke(query)
        retrieved_docs = [doc.page_content for doc in docs]
        return {
            "query": query,
            "retrieved_docs": retrieved_docs
        }
