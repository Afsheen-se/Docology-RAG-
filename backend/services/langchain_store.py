import os
from typing import List, Dict, Optional
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.sentence_transformer import SentenceTransformerEmbeddings


class LangChainStore:
    """A thin wrapper around LangChain's Chroma to align with our VectorStore API."""

    def __init__(self):
        self.chroma_dir = os.getenv("LC_CHROMA_DIR", "./data/lc_persisted")
        self.collection_name = os.getenv("LC_COLLECTION", "docology_documents_lc")
        self.embed_model = os.getenv("LC_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.store: Optional[Chroma] = None
        self.embedder = None

    async def initialize(self):
        os.makedirs(self.chroma_dir, exist_ok=True)
        # Create embeddings
        self.embedder = SentenceTransformerEmbeddings(model_name=self.embed_model)
        # Initialize persisted Chroma store (LangChain wrapper manages collection internally)
        self.store = Chroma(
            collection_name=self.collection_name,
            embedding_function=self.embedder,
            persist_directory=self.chroma_dir,
        )

    async def add_document(self, document_id: str, chunks: List[str], metadata: List[Dict]):
        if not self.store:
            raise Exception("LangChainStore not initialized")
        metadatas = []
        for i, meta in enumerate(metadata):
            metadatas.append({
                "document_id": document_id,
                "filename": meta.get("filename"),
                "page": meta.get("page"),
                "chunk_index": meta.get("chunk_index"),
                "created_at": datetime.now().isoformat(),
            })
        # Add texts with metadata
        self.store.add_texts(texts=chunks, metadatas=metadatas)
        # Persist to disk
        self.store.persist()

    async def search(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[Dict]:
        if not self.store:
            raise Exception("LangChainStore not initialized")
        where = None
        if document_ids:
            where = {"document_id": {"$in": document_ids}}
        results = self.store.similarity_search_with_relevance_scores(query, k=top_k, filter=where)
        # results: List[Tuple[Document, score]] where lower score = more similar in LC? With Chroma, higher score is better relevance score (1-score?)
        out = []
        for doc, score in results:
            out.append({
                "text": doc.page_content,
                "metadata": doc.metadata,
                "distance": 1 - float(score) if score is not None else None,
            })
        return out

    async def clear(self):
        if self.store:
            self.store.delete_collection()
            self.store.persist()
