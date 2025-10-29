#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import glob
import logging

import faiss
import tqdm
from langchain_community.docstore import InMemoryDocstore
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

data_dir = 'data/interm/blender_python_reference_4_5/'
raw = 'data/raw'
db_save_dir = 'vectorstores/faiss_full'


def build_vectorstore():
    # dir_loader = PyPDFDirectoryLoader(
    #     path=data_dir,
    #     # glob=r"**/*.pdf",
    #     recursive=False,
    #     silent_errors=False,
    #     password=None,
    #     extract_images=False,
    #     load_hidden=False,
    # )
    #
    # logger.info("Load directory pdfs")
    # docs = dir_loader.load()

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

    logger.info(f"Save vectorstore to {db_save_dir}")
    vector_store.save_local(folder_path=db_save_dir)
