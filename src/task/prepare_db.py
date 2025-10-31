#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import glob
import logging
from typing import Any

import faiss
import tqdm
from langchain_community.docstore import InMemoryDocstore
from langchain_community.document_loaders import PyPDFLoader, PythonLoader
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_embedding_model(model_name: str = "all-MiniLM-L6-v2.gguf2.f16.gguf"):
    gpt4all_kwargs = {'allow_download': 'True'}
    embeddings = GPT4AllEmbeddings(
        model_name=model_name,
        gpt4all_kwargs=gpt4all_kwargs,
    )

    return embeddings


def load_vector_store(db_dir, embedding: str | Any = None):
    if embedding is None:
        embedding = load_embedding_model()
    elif isinstance(embedding, str):
        embedding = load_embedding_model(embedding)
    else:
        pass

    db = FAISS.load_local(
        folder_path=db_dir,
        embeddings=embedding,
        allow_dangerous_deserialization=True
    )

    return db


def build_vectorstore(data_dir, db_dir):
    logger.info("Initialize embedding model")
    embedding_model = GPT4AllEmbeddings()
    embed_dim = len(embedding_model.embed_query('hello'))

    logger.info('Create index')
    index = faiss.IndexFlatL2(embed_dim)

    logger.info('Create vector store')
    vector_store = FAISS(
        embedding_function=embedding_model,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )

    pdf_files = glob.glob(fr'{data_dir}/*.pdf')

    batch_size = 20
    for i in tqdm.tqdm(range(0, len(pdf_files), batch_size)):
        batch_files = pdf_files[i:i + batch_size]
        batch_docs = []
        for file in tqdm.tqdm(batch_files):
            loader = PyPDFLoader(file)
            docs = loader.lazy_load()
            batch_docs.extend(docs)

        chunks = text_splitter.split_documents(batch_docs)
        vector_store.add_documents(chunks)

    logger.info(f"Save vectorstore to {db_dir}")
    vector_store.save_local(folder_path=db_dir)


def extend_vectorstore_py_file(db_dir, file):
    logger.info(f"Load vectorstore from '{db_dir}'")
    vector_store = load_vector_store(db_dir=db_dir)

    logger.info(f"Load Python file: '{file}'")
    loader = PythonLoader(file_path=file)
    doc = loader.lazy_load()

    logger.info("Add python document to vector store")
    vector_store.add_documents(documents=list(doc))

    logger.info(f"Save vectorstore to {db_dir}")
    vector_store.save_local(folder_path=db_dir)
