#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

from langchain.chat_models import init_chat_model
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_save_dir = 'vectorstores/faiss'


def build_chain():
    logger.info("Instantiate embedding model")
    embedding_model = GPT4AllEmbeddings()

    logger.info("Load local vectorstore")
    vector_db = FAISS.load_local(
        folder_path=db_save_dir,
        embeddings=embedding_model,
        allow_dangerous_deserialization=True
    )

    logger.info("Get retriever")
    retriever = vector_db.as_retriever(search_type='similarity', search_kwargs={'k': 3})

    logger.info("Initialize chat model")
    chat_model = init_chat_model(model='gpt-4o-mini')

    logger.info("Make chain")
    prompt = "{context} - {question}"

    prompt = ChatPromptTemplate.from_template(prompt)

    ret = RunnableLambda(lambda x: {'context': retriever.invoke(x), 'question': x})

    # llm_chain = RunnableSequence(first=prompt, last=chat_model)
    chain = ret | prompt | chat_model

    print(chain)

    response = chain.invoke("create 4 legs by blender code")
    print(response.content)
