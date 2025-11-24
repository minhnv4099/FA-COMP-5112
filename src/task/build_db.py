#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
import os
import sys
sys.path.append(os.getcwd())
import glob
import logging

import faiss
import tqdm
import fitz
import re

from typing import Any
from langchain_community.docstore import InMemoryDocstore
from langchain_community.document_loaders import PythonLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.utils.decorator import add_note_docstring
from src.utils.embeddings import load_openai_embeddings, load_gpt4all_embeddings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_vector_store(db_dir, embedding: str | Any = None):
    embeddings = load_openai_embeddings()

    db = FAISS.load_local(
        folder_path=db_dir,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

    return db


def build_vectorstore(doc_dir, db_dir):
    logger.info("Initialize embedding model")
    embedding_model = load_openai_embeddings()
    embed_dim = len(embedding_model.embed_query('hello'))

    logger.info('Create vector store')
    index = faiss.IndexFlatL2(embed_dim)
    vector_store = FAISS(
        embedding_function=embedding_model,
        index=index,
        docstore=InMemoryDocstore(),
        index_to_docstore_id={},
    )

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=300,
    )

    pdf_files = glob.glob(fr'{doc_dir}/**/*.pdf', recursive=True)
    logger.info(f"Total files: {len(pdf_files)}")

    all_chunks = []
    batch_size = 20
    for i in tqdm.tqdm(range(0, len(pdf_files), batch_size)):
        batch_files = pdf_files[i:i + batch_size]
        batch_chunks = []
        for file in tqdm.tqdm(batch_files):

            try:
                text = extract_text_pdfminer(file)
                text = clean_text(text)
            except Exception:
                continue

            chunks = text_splitter.split_text(text)
            batch_chunks.extend(chunks)

        all_chunks.extend(batch_chunks)

        logger.info(f"Chunk size: {len(batch_chunks)}\n")
        if batch_chunks:
            vector_store.add_texts(batch_chunks)
            ...

    logger.info(f"All chunks: {len(all_chunks)}")

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


def clean_text(t):
    t = re.sub(r'\s+\n', '\n', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = t.replace('\t', ' ')
    return t.strip()


@add_note_docstring('No good as extract_text_pdfminer')
def plain_extract_text(path):
    doc = fitz.open(path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text


@add_note_docstring("Use Second time, first time use ``PyPDFLoader``")
def extract_text_pdfminer(path_file):
    from pdfminer.high_level import extract_text

    text = extract_text(path_file)
    return text


@add_note_docstring("Consider later")
def extract_text_unstructured(path_file):
    from unstructured.partition.pdf import partition_pdf
    import os
    os.environ['OCR_AGENT'] = 'tesseract'
    elements = partition_pdf(
        filename=path_file,
        strategy="hi_res",
        extract_images_in_pdf=True,
        infer_table_structure=True,
    )

    text = ''
    for ele in elements:
        text += ele.text + '\n'

    return text


if __name__ == '__main__':
    DOC_DIR = "data/interm/blender_python_reference_4_0"
    DB_DIR = "vectorstores/blender/faiss_pdfminer/"
    # build_vectorstore(DOC_DIR, DB_DIR)
