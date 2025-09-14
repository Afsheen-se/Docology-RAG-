import chromadb
from chromadb.config import Settings
import os
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import uuid
from datetime import datetime
from models.document import DocumentResponse

class VectorStore:
    def __init__(self):
        self.chroma_dir = os.getenv("CHROMA_DIR", "./data/persisted")
        self.client = None
        self.collection = None
        self.embedder = None
    
    async def initialize(self):
        """Initialize ChromaDB and embedding model"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.chroma_dir, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.chroma_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="docology_documents",
                metadata={"hnsw:space": "cosine"}
            )
            
            # Initialize embedding model
            self.embedder = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
            
            print("Vector store initialized successfully")
            
        except Exception as e:
            raise Exception(f"Failed to initialize vector store: {str(e)}")
    
    async def add_document(self, document_id: str, chunks: List[str], metadata: List[Dict]):
        """Add document chunks to vector store"""
        try:
            if not self.collection or not self.embedder:
                raise Exception("Vector store not initialized")
            
            # Generate embeddings
            embeddings = self.embedder.encode(chunks).tolist()
            
            # Prepare data for ChromaDB
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]
            metadatas = []
            
            for i, meta in enumerate(metadata):
                metadatas.append({
                    "document_id": document_id,
                    "filename": meta["filename"],
                    "page": meta["page"],
                    "chunk_index": meta["chunk_index"],
                    "created_at": datetime.now().isoformat()
                })
            
            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=chunks,
                metadatas=metadatas
            )
            
            print(f"Added {len(chunks)} chunks for document {document_id}")
            
        except Exception as e:
            raise Exception(f"Failed to add document to vector store: {str(e)}")
    
    async def search(self, query: str, top_k: int = 5, document_ids: Optional[List[str]] = None) -> List[Dict]:
        """Search for relevant chunks"""
        try:
            if not self.collection or not self.embedder:
                raise Exception("Vector store not initialized")
            
            # Generate query embedding
            query_embedding = self.embedder.encode([query]).tolist()[0]
            
            # Prepare where clause for document filtering
            where_clause = None
            if document_ids:
                where_clause = {"document_id": {"$in": document_ids}}
            
            # Search with MMR (Maximal Marginal Relevance)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            chunks = []
            if results["documents"] and results["documents"][0]:
                for i, doc in enumerate(results["documents"][0]):
                    chunks.append({
                        "text": doc,
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            return chunks
            
        except Exception as e:
            raise Exception(f"Failed to search vector store: {str(e)}")
    
    async def list_documents(self) -> List[DocumentResponse]:
        """List all unique documents in the collection"""
        try:
            if not self.collection:
                raise Exception("Vector store not initialized")
            
            # Get all documents
            results = self.collection.get(include=["metadatas"])
            
            # Group by document_id
            documents = {}
            for i, metadata in enumerate(results["metadatas"]):
                doc_id = metadata["document_id"]
                if doc_id not in documents:
                    documents[doc_id] = {
                        "id": doc_id,
                        "filename": metadata["filename"],
                        "pages": 0,
                        "size": 0,
                        "created_at": metadata["created_at"]
                    }
                
                # Count pages (approximate)
                if metadata["page"] != "Unknown":
                    try:
                        page_num = int(metadata["page"])
                        documents[doc_id]["pages"] = max(documents[doc_id]["pages"], page_num)
                    except:
                        pass
            
            return list(documents.values())
            
        except Exception as e:
            raise Exception(f"Failed to list documents: {str(e)}")
    
    async def delete_document(self, document_id: str):
        """Delete a document and all its chunks"""
        try:
            if not self.collection:
                raise Exception("Vector store not initialized")
            
            # Get all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id},
                include=["ids"]
            )
            
            if results["ids"]:
                # Delete all chunks
                self.collection.delete(ids=results["ids"])
                print(f"Deleted document {document_id} with {len(results['ids'])} chunks")
            
        except Exception as e:
            raise Exception(f"Failed to delete document: {str(e)}")
