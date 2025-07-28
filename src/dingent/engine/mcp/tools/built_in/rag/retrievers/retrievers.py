from functools import lru_cache
from typing import Literal

import chromadb
from langchain_chroma import Chroma
from langchain_community.embeddings import InfinityEmbeddings

from mcp_servers.core.settings import get_settings

settings = get_settings()
embeddings = InfinityEmbeddings(
    model="Linq-AI-Research/Linq-Embed-Mistral",
    infinity_api_url="http://192.168.164.110:7997",
)
client = chromadb.HttpClient(host="192.168.164.110", port=8008)
ID_KEY = "doc_id"

all_collections = Literal["GSA", "GenBase"]


@lru_cache
def get_vectorstore(collection_name: all_collections):
    vectorstore = Chroma(
        collection_name=collection_name,
        client=client,
        embedding_function=embeddings,
        collection_metadata={"hnsw:space": "cosine"},
    )
    return vectorstore
