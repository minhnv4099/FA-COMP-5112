#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import logging

import faiss
from langchain_community.docstore import InMemoryDocstore
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

data_dir = 'data/raw'
db_save_dir = 'vectorstores/faiss'


def build_vectorstore():
    # loader = PyPDFLoader("data/interm/blender_python_reference_4_5/bpy_extras.io_utils.pdf")
    dir_loader = PyPDFDirectoryLoader(
        path=data_dir,
        glob=r"**/*.pdf",
        mode="single",
        recursive=False,
        silent_errors=False,
        password=None,
        extract_images=False,
        load_hidden=False,
    )

    logger.info("Load directory pdfs")
    docs = dir_loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
    )

    logger.info("Split docs")
    chunks = text_splitter.split_documents(docs)

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

    logger.info('Add chunks (documents) to vectorstore')
    vector_store.add_documents(documents=chunks)

    logger.info(f"Save vectorstore to {db_save_dir}")
    vector_store.save_local(folder_path=db_save_dir)
