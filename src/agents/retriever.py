#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from typing import Any, Literal, Optional

from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langgraph.config import RunnableConfig
from langgraph.runtime import Runtime
from langgraph.types import Command
from typing_extensions import override

from src.base.agent import AgentAsNode, register
from src.base.typing import InputT


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
            runtime: Optional[Runtime] = None,
            context: Optional[Runtime] = None,
            config: Optional[Runtime[RunnableConfig]] = None,
            **kwargs
    ) -> Command[Literal['coding']]:
        print("retrieve", state, sep='\n\t')
        query_docs = list()
        for i, query in enumerate(state['queries']):
            docs = self.retrieving_engine.invoke(query)
            query_docs.append((query, [doc.page_content for doc in docs]))

        update_state = {
            'coding_task': state['coding_task'],
            'retrieved_docs': query_docs,
            "messages":
                {'role': f"assistant",
                 "content": f"Retriever Agent result documents when '{runtime.context['coding_task']}'"}
        }

        return Command(
            update=update_state,
            goto="coding"
        )
