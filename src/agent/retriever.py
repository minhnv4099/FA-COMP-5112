#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from __future__ import annotations

import logging
from typing import (
    Literal,
    Union,
    Generic,
    Optional,
    TYPE_CHECKING,
    cast,
)
from typing_extensions import override, deprecated

from langgraph.graph.state import END
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command
from langchain_openai import ChatOpenAI

from src.registry import RegisterNode, RegisterAgent
from src.types import StateT, ContextT, InputT, OutputT
from src.node.base import BaseNode
from src.base.utils import DirectionRouter
from src.utils.decorator import add_note_docstring
from src.chat_output.retriever import RetrievingCategory

if TYPE_CHECKING:
    from src.state.comp_5112 import RetrieverState
    from src.message.parsed_tool_call import ParsedTollCallMessage

logger = logging.getLogger(__name__)


@add_note_docstring(docs="'COMP-5112' project")
@RegisterAgent(module_path=__name__, name='retriever')
@RegisterNode(module_path=__name__, name='retriever')
class RetrieverAgent(
    BaseNode,
    Generic[StateT, ContextT, InputT, OutputT],
    node_name="Retriever",
    use_model=True
):
    # TODO: add docs
    """The Retriever Agent class"""

    # def __init__(
    #     self,
    #     *args,
    #     embedding_name: str = None,
    #     n_docs: int = None,
    #     db_path: str = None,
    #     **kwargs
    # ):
    #     super().__init__(*args, **kwargs, )
    #
    #     # # TODO: consider other model
    #     # gpt4all_kwargs = {'allow_download': 'True'}
    #     # self.embedding = GPT4AllEmbeddings(
    #     #     model_name=embedding_name,
    #     #     gpt4all_kwargs=gpt4all_kwargs,
    #     #     client=None
    #     # )
    #     #
    #     # logger.info(f'Load vectorstore in "{db_path}"')
    #     # # TODO: consider other db
    #     # self.db_path = db_path
    #     # self.db = FAISS.load_local(
    #     #     folder_path=self.db_path,
    #     #     embeddings=self.embedding,
    #     #     allow_dangerous_deserialization=True,
    #     # )
    #     # self.retrieving_engine = self.db.as_retriever(
    #     #     search_type='similarity',
    #     #     search_kwargs={
    #     #         'k': n_docs,
    #     #     },
    #     # )
    #
    #     # self.chain = RunnableLambda(self._retrieve) | self.chat_template | self.chat_model
    #     self._set_system_behavior(
    #         config=self.config,
    #         system_prompt=self.system_prompt.format()
    #     )

    @add_note_docstring("Used for only COMP 5112")
    @override
    def __call__(
        self,
        state: RetrieverState,
        config: Optional[RunnableConfig] = None,
        *,
        runtime: Optional[Runtime[ContextT]] = None,
        **kwargs
    ) -> Union[OutputT, Command[Literal['coding']], OutputT]:
        # TODO: add docs
        """"""
        logger.info(self.opening_symbols)

        retrieved_docs: dict[int, list] = dict()
        category = None

        for i, query in enumerate(state['queries']):
            # all requires are the same category
            separator = '\n' if category == 'fix' else ''
            logger.info(f"query {i + 1}/{len(state['queries'])}: {separator}{query}")

            # if category is None:
            #     category = self.before_model(query).category
            # config = self.get_config_on_category(category)

            # TODO: dynamic config
            config = self.config

            # -------------------------------------------------
            formatted_prompt = self.human_template.format(query=query)

            # No needed, but provide insight
            message = self.invoke(
                input=formatted_prompt,
                config=config
            )

            response = self.process_response(self.get_desired_result(
                message=message,
                keys_to_get='summary',
                default=''
            ))
            # -------------------------------------------------
            retrieved_docs[i] = response

        messages = self.get_messages(config)
        self._finish_session(logger)

        update_state = {
            'coding_task': state['coding_task'],
            'queries': state['queries'],
            'retrieved_docs': retrieved_docs,
            'caller': 'retriever',
            'is_sub_call': True,
            'has_docs': True,
            "messages": messages
        }

        # return update_state
        return DirectionRouter.goto(state=update_state, node=END, method='command')

    def before_model(self, query: str) -> RetrievingCategory:
        return self.category_classifier.invoke(
            input=[
                {'role': 'user', 'content': f'classify the query: {query}'}
            ]
        )

    def get_config_on_category(self, category: str):
        return self.config_dict[category]['config']

    @deprecated('Now no need')
    def dynamic_system_prompt(self):
        # TODO: write middleware class integrate this
        # set a small model to classify query
        self.category_classifier = ChatOpenAI(
            openai_api_base='https://openrouter.ai/api/v1',  # type: ignore
            model='meta-llama/llama-3.2-3b-instruct',
            openai_api_key=self.model_api_key,  # type: ignore
            temperature=0.3,
            # rate_limiter=InMemoryRateLimiter(
            #     requests_per_second=0.1,
            #     check_every_n_seconds=0.1,
            #     max_bucket_size=10
            # ),
        ).with_structured_output(
            schema=RetrievingCategory,
            include_raw=False,
            strict=True,
        )

        # NOTE: use own config
        self.config_dict = {
            cat: {
                'config': RunnableConfig(
                    recursion_limit=200,
                    configurable={
                        'thread_id': f"{self.name}_to_{cat}",
                    }
                ),
                'system_prompt': self.system_prompt
            }
            for cat in ['fix', 'create', 'enhance', 'search', 'greeting']
        }

        # set system prompt for each ...
        for k, v in self.config_dict.items():
            self._set_system_behavior(
                config=v['config'],
                system_prompt=v['system_prompt']
            )
