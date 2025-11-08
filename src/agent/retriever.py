#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging
from typing import Literal, Union

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import override

from src.base.node import AgentAsNode
from src.base.utils import DirectionRouter
from src.registry import RegisterNode, RegisterAgent
from src.types import InputT, OutputT
from src.utils.decorator import add_note_docstring

logger = logging.getLogger(__name__)


@add_note_docstring(docs="Used for only 'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='retriever')
@RegisterNode(module_path=__name__, name='retriever')
class RetrieverAgent(AgentAsNode, node_name="Retriever", use_model=True):
    """The Retriever Agent class"""

    def __init__(
            self,
            *args,
            embedding_name: str = None,
            n_docs: int = None,
            db_path: str = None,
            **kwargs
    ):
        super().__init__(*args, **kwargs, )

        gpt4all_kwargs = {'allow_download': 'True'}
        self.embedding = GPT4AllEmbeddings(
            model_name=embedding_name,
            gpt4all_kwargs=gpt4all_kwargs,
            client=None
        )

        logger.info(f'Load vectorstore in "{db_path}"')
        self.db_path = db_path
        self.db = FAISS.load_local(
            folder_path=self.db_path,
            embeddings=self.embedding,
            allow_dangerous_deserialization=True,
        )
        self.retrieving_engine = self.db.as_retriever(
            search_type='similarity',
            search_kwargs={'k': n_docs}
        )

        # self.chain = RunnableLambda(self._retrieve) | self.chat_template | self.chat_model

    @override
    def __call__(
            self,
            state: InputT | dict,
            runtime: Runtime[RunnableConfig] = None,
            context: Runtime[RunnableConfig] = None,
            config: RunnableConfig = None,
            **kwargs
    ) -> Union[OutputT, Command[Literal['coding']], OutputT]:
        """"""

        logger.info(self.opening_symbols)

        conversation = []
        retrieved_docs: dict[int, list] = dict()

        for i, query in enumerate(state['queries']):
            separator = '\n' if state['coding_task'] == 'fix' else ''
            logger.info(f"query {i + 1}/{len(state['queries'])}: {separator}{query}")

            docs = self.retrieving_engine.invoke(query)
            # -------------------------------------------------
            formatted_template = self._get_pretty_formatted_prompt(
                chat_prompt_template=self.chat_template,
                input={
                    'query': query,
                    'retrieved_docs': docs
                }
            )
            summary, _messages = self.chat_model_call(formatted_template)
            # -------------------------------------------------
            retrieved_docs[i] = summary

            conversation = self._extend_conversation(messages=_messages, his_conversation=conversation)

        self._finish_session(logger, conversation)

        update_state = {
            'coding_task': state['coding_task'],
            'queries': state['queries'],
            'retrieved_docs': retrieved_docs,
            'caller': 'retriever',
            'is_sub_call': True,
            'has_docs': True,
            "messages": conversation
        }

        # return update_state
        return DirectionRouter.goto(state=update_state, node='coding', method='command')

    def _retrieve(self, query):
        docs = self.retrieving_engine.invoke(query)
        retrieved_docs = [doc.page_content for doc in docs]
        return {
            "query": query,
            "retrieved_docs": retrieved_docs
        }
