#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace


class BaseChatWrapper:
    def __init__(
            self,
            repo_id: str = None,
            huggingfacehub_api_token: str = None,
            **kwargs
    ):
        if repo_id is None:
            repo_id = "mistralai/Mistral-7B-Instruct-v0.3"

        self.api_key = huggingfacehub_api_token
        self.repo_id = repo_id

        self.chat_model = ChatHuggingFace(
            llm=HuggingFaceEndpoint(
                repo_id=self.repo_id,
                huggingfacehub_api_token=self.api_key,
            )
        )

    def invoke(self, messages):
        return self.chat_model.invoke(messages)


def main():
    question = "Break 'create a 3D chair' into smaller ones with context of Blender code just code context, not navigation, return by list of subtasks"
    HUGGINGFACEHUB_API_TOKEN = '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'

    from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate

    prompt = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template("You're a helpful assistant."),
        HumanMessagePromptTemplate.from_template("{user_question}"),
    ])

    chat = BaseChatWrapper()
    messages = prompt.invoke({"user_question": question})

    response = chat.invoke(messages)
    print(response.content)


if __name__ == '__main__':
    main()
