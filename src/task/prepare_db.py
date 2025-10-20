#
#  Copyright (c) 2025
#  Minh NGUYEN <vnguyen9@lakeheadu.ca>
#
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain_community.vectorstores import FAISS

texts = [
    "Legs of a chair can be made by some kinds of materials such as wood, mental. Wood help the chair be more elegant",
    "Scientifically designed backrest can help users project their back by always keeping back at comfortable position and pose",
    "Legs often are about 40-50 centimeters",
    "Colors of green or blue are most used ones because of satisfaction"
]

embedding = GPT4AllEmbeddings()
vector_store = FAISS.from_texts(texts, embedding)

vector_store.save_local("vectorstores/faiss")
