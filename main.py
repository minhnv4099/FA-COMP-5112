#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from src.builder import Builder
from src.utils import find_load_env

find_load_env()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    chat = Builder.build(
        type='agent',
        config={
            'name': 'retriever',
            'model_name': 'openai/gpt-4o-mini',  # TODO: can change
            'template_file': 'templates/prompt/general/retriever.yaml',   # TODO: finetune system prompt
            'tool_schemas': [
                {
                    'type': 'tool',
                    'name': 'retrieve_query',
                    'tool_kwargs': {
                        "db_path": "vectorstores/lakehead/faiss_v.1",  # NOTE: keep it for testing
                        "embedding_name": "all-MiniLM-L6-v2.gguf2.f16.gguf",  # NOTE: keep it for testing
                        "n_docs": 4  # TODO: can change
                    }
                },
            ]
        }
    )

    # config = {'configurable': {'thread_id': 'single_user'}}
    while True:
        question = input('Enter your question (q to quit): ')
        if question == 'q':
            print('Goodbye. Have a nice day.')
            break

        response = chat.invoke(question)

        print(response.content or response.tool_calls)

    # to see full conversation to inspect insights
    chat.print_conversation()


if __name__ == '__main__':
    main()
