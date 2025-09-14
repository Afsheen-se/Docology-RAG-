from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
from datetime import datetime
import json
from dotenv import load_dotenv
from contextlib import asynccontextmanager

# Load environment variables from .env file
load_dotenv()

from services.document_processor import DocumentProcessor
from services.vector_store import VectorStore
from services.llm_service import LLMService
from models.document import Document, DocumentResponse
from models.query import QueryRequest, QueryResponse

# Initialize services
document_processor = DocumentProcessor()

# Choose retrieval backend: Chroma direct (default) or LangChain wrapper
USE_LANGCHAIN = os.getenv("USE_LANGCHAIN", "false").lower() == "true"
retrieval_store = None
if USE_LANGCHAIN:
    try:
        # Import lazily so the app runs even if langchain isn't installed
        from services.langchain_store import LangChainStore  # type: ignore
        retrieval_store = LangChainStore()
    except Exception as e:
        print(f"LangChain not available ({e}); falling back to direct Chroma VectorStore.")
        retrieval_store = VectorStore()
else:
    retrieval_store = VectorStore()

llm_service = LLMService()

# Helper to (re)index a saved file on disk
async def _index_saved_file(file_path: str, filename_on_disk: str):
    try:
        doc_id = filename_on_disk.split('_')[0]
        original_name = filename_on_disk.split('_', 1)[1] if '_' in filename_on_disk else filename_on_disk
        processed = await document_processor.process_document(
            file_path=file_path,
            document_id=doc_id,
            filename=original_name
        )
        chunks = processed.get("chunks", [])
        metadata = processed.get("metadata", [])
        if chunks:
            await vector_store.add_document(document_id=doc_id, chunks=chunks, metadata=metadata)
            print(f"Reindexed {original_name}: {len(chunks)} chunks")
        else:
            print(f"No extractable text for {original_name}; skipped indexing")
        return {"document_id": doc_id, "filename": original_name, "chunks": len(chunks)}
    except Exception as e:
        print(f"Failed to index {filename_on_disk}: {str(e)}")
        return {"document_id": None, "filename": filename_on_disk, "error": str(e)}

# --- Presentation helpers ----------------------------------------------------
def _bold_headings_and_clean(text: str) -> str:
    """Make headings bold, remove asterisks, and normalize bullets.
    Heuristics:
    - Lines ending with ':' and mostly uppercase become bold.
    - Replace leading '- ' or '* ' with '• '.
    - Strip stray '*'.
    """
    import re
    lines = text.splitlines()
    out = []
    for line in lines:
        # Normalize list markers
        line = re.sub(r"^\s*[-*]\s+", "• ", line)
        # Remove stray asterisks anywhere
        line = line.replace("*", "")
        # Bold headings (UPPERCASE and ending with ':')
        stripped = line.strip()
        if stripped.endswith(":"):
            # Count uppercase proportion
            letters = re.sub(r"[^A-Za-z]", "", stripped[:-1])
            upper = sum(1 for c in letters if c.isupper())
            if letters and upper / max(1, len(letters)) > 0.6:
                line = f"**{stripped}**"
        out.append(line)
    return "\n".join(out).strip()

def _format_references(citations: list, single_doc: bool) -> str:
    # Deduplicate while preserving order
    seen = set()
    items = []
    for c in citations or []:
        key = (c.get("filename"), str(c.get("page")))
        if key not in seen:
            seen.add(key)
            items.append(key)
    if not items:
        return ""
    lines = ["", "**REFERENCES:**"]
    for filename, page in items:
        if single_doc:
            lines.append(f"• Page {page}")
        else:
            lines.append(f"• {filename}, p. {page}")
    return "\n".join(lines)

def _add_inline_citations(text: str, citations: list, single_doc: bool):
    """Append rotating inline citations to content and return (text, used_citations).
    Headings are lines that are bolded **...:** or end with ':'.
    Only citations actually inserted will be returned in used_citations.
    """
    if not citations:
        return text, []
    lines = text.splitlines()
    out = []
    used = []
    idx = 0
    for line in lines:
        stripped = line.strip()
        is_heading = stripped.endswith(":") or (stripped.startswith("**") and stripped.endswith("**") and stripped[:-2].endswith(":"))
        if stripped and not is_heading:
            c = citations[idx % len(citations)]
            filename = c.get("filename", "")
            page = c.get("page", "?")
            cite = f"(p. {page})" if single_doc else f"({filename}, p. {page})"
            if not stripped.endswith(")"):
                line = f"{line} {cite}"
                used.append({"filename": filename, "page": page})
            idx += 1
        out.append(line)
    # Deduplicate used citations while preserving order
    seen = set()
    dedup_used = []
    for u in used:
        key = (u.get("filename"), str(u.get("page")))
        if key not in seen:
            seen.add(key)
            dedup_used.append(u)
    return "\n".join(out), dedup_used

def _add_section_gaps(text: str, single_doc: bool) -> str:
    """Insert a blank line when the inline citation's filename changes between lines.
    Looks for trailing pattern '(filename, p. X)'. For single_doc, returns as-is.
    """
    if single_doc:
        return text
    import re
    pattern = re.compile(r"\((?P<filename>.+?), p\. \d+\)\s*$")
    lines = text.splitlines()
    out = []
    prev_file = None
    for line in lines:
        m = pattern.search(line)
        curr_file = m.group('filename') if m else None
        if prev_file is not None and curr_file is not None and curr_file != prev_file:
            # Insert a visual gap between summaries
            if out and out[-1] != "":
                out.append("")
        out.append(line)
        if curr_file:
            prev_file = curr_file
    return "\n".join(out)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Initializing retrieval store (LangChain=" + str(USE_LANGCHAIN) + ")...")
    await retrieval_store.initialize()
    print("Retrieval store initialized successfully")
    yield
    # Shutdown
    print("Shutting down...")

# Create FastAPI app with lifespan
app = FastAPI(title="Docology API", version="1.0.0", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    size: int
    message: str

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document (PDF/DOCX/TXT)"""
    try:
        print(f"=== UPLOAD START ===")
        print(f"Filename: {file.filename}")
        print(f"Content type: {file.content_type}")
        print(f"File size: {file.size if hasattr(file, 'size') else 'unknown'}")
        
        # Generate unique document ID
        document_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = "./data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # Simple filename handling
        safe_filename = file.filename.replace(" ", "_").replace("/", "_")
        file_path = os.path.join(upload_dir, f"{document_id}_{safe_filename}")
        
        print(f"Saving to: {file_path}")
        
        # Read and save file
        content = await file.read()
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        print(f"File saved! Size: {len(content)} bytes")

        pages = 1
        indexing_warning = None
        try:
            # Process the document into chunks and index into the vector store
            processed = await document_processor.process_document(
                file_path=file_path,
                document_id=document_id,
                filename=file.filename
            )
            pages = processed.get("pages", 1)
            chunks = processed.get("chunks", [])
            metadata = processed.get("metadata", [])
            print(f"Processing complete. Chunks: {len(chunks)}, Pages: {pages}")

            if chunks:
                await retrieval_store.add_document(document_id=document_id, chunks=chunks, metadata=metadata)
                print("Indexed document into retrieval store")
            else:
                indexing_warning = "No extractable text found; uploaded but not indexed."
                print("Warning: No chunks extracted from the document. It may be scanned or empty.")
        except Exception as e:
            indexing_warning = f"Uploaded, but indexing failed: {str(e)}"
            print(f"Indexing error (non-fatal): {str(e)}")
            import traceback
            traceback.print_exc()

        print(f"=== UPLOAD SUCCESS ===")
        
        # Return response with page count and any warning
        resp = {
            "document_id": document_id,
            "filename": file.filename,
            "pages": pages,
            "size": len(content),
            "message": "Document uploaded successfully"
        }
        if indexing_warning:
            resp["warning"] = indexing_warning
        return resp
        
    except Exception as e:
        print(f"=== UPLOAD ERROR ===")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        return {"error": f"Upload failed: {str(e)}"}

@app.post("/ask")
async def ask_question(request: QueryRequest):
    """Ask a question and get response"""
    try:
        print(f"=== CHAT REQUEST ===")
        print(f"Query: {request.query}")
        print(f"Document IDs: {request.document_ids}")
        
        # Process documents and extract content
        upload_dir = "./data/uploads"
        relevant_content = []
        citations = []
        
        # Get list of files to process
        files_to_process = []
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.endswith(('.pdf', '.docx', '.txt')):
                    # If specific documents are selected, only process those
                    if request.document_ids:
                        file_id = filename.split('_')[0]
                        print(f"Checking file: {filename}, extracted ID: {file_id}, looking for: {request.document_ids}")
                        if file_id in request.document_ids:
                            files_to_process.append(filename)
                            print(f"Added to process: {filename}")
                    else:
                        # Process all files if no specific selection
                        files_to_process.append(filename)
                        print(f"Added to process (all): {filename}")
        
        print(f"Processing {len(files_to_process)} files...")
        
        # If no files found with specific IDs, process all files as fallback
        if not files_to_process and request.document_ids:
            print("No files found with specific IDs, processing all files as fallback...")
            for filename in os.listdir(upload_dir):
                if filename.endswith(('.pdf', '.docx', '.txt')):
                    files_to_process.append(filename)
        
        print(f"Final files to process: {files_to_process}")
        
        # Process each file and extract relevant content
        for filename in files_to_process:
            file_path = os.path.join(upload_dir, filename)
            
            try:
                # Use the document processor to handle different file types
                document_id = filename.split('_')[0]
                file_extension = os.path.splitext(filename)[1].lower()
                
                # Process the document based on its type
                if file_extension == '.pdf':
                    result = await document_processor._process_pdf(file_path, document_id, filename)
                elif file_extension == '.docx':
                    result = await document_processor._process_docx(file_path, document_id, filename)
                elif file_extension == '.txt':
                    result = await document_processor._process_txt(file_path, document_id, filename)
                else:
                    print(f"Unsupported file type: {file_extension}")
                    continue
                
                # Add the processed content to our results
                if result and 'chunks' in result and result['chunks']:
                    # Combine chunks for this document
                    doc_content = "\n\n".join([f"[Document: {filename}, Page {meta.get('page', '?')}]\n{chunk}" 
                                          for chunk, meta in zip(result['chunks'], result['metadata'])])
                    
                    relevant_content.append({
                        'filename': filename,
                        'content': doc_content,
                        'metadata': result['metadata']
                    })
                    
                    # Add citation for this document
                    citations.append({
                        'filename': filename.split('_', 1)[1] if '_' in filename else filename,
                        'page': 'Multiple' if len(result['metadata']) > 1 else result['metadata'][0].get('page', '1')
                    })
                    
                    print(f"Processed {filename}: {len(doc_content)} characters")
                
            except Exception as e:
                print(f"Error processing {filename}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # If multiple docs are selected, build a summary per doc
        if request.document_ids and len(request.document_ids) > 1:
            sections = []
            all_used_citations = []
            for doc_id in request.document_ids:
                try:
                    per_doc = await retrieval_store.search(
                        query=request.query,
                        top_k=6,
                        document_ids=[doc_id]
                    )
                except Exception as e:
                    print(f"Vector search failed for {doc_id}: {str(e)}")
                    per_doc = []

                if not per_doc:
                    continue

                # Compose context and citations for this doc
                per_citations = []
                parts = []
                doc_display = None
                for item in per_doc:
                    meta = item.get("metadata", {})
                    filename = meta.get("filename", f"Document {doc_id}")
                    if not doc_display:
                        doc_display = filename
                    page = meta.get("page", "?")
                    per_citations.append({"filename": filename, "page": page})
                    parts.append(f"[Source: {filename}, page {page}]\n{item.get('text', '')}")
                context = "\n\n".join(parts)

                # Generate response per doc
                content_chunks = []
                async for chunk in llm_service.generate_response(
                    query=request.query,
                    context=context,
                    citations=per_citations
                ):
                    content_chunks.append(chunk)
                doc_answer = "".join(content_chunks).strip()
                doc_answer = _bold_headings_and_clean(doc_answer)
                # Multi-doc mode: include filename in inline citations
                doc_answer, used = _add_inline_citations(doc_answer, per_citations, single_doc=False)
                all_used_citations.extend(used)
                # Add a clear heading per document
                heading = f"**{(doc_display or doc_id)}:**"
                sections.append(f"{heading}\n{doc_answer}")

            if sections:
                final_text = "\n\n".join(sections)
                # Add gaps for readability across documents (no-op for single_doc=False handled already by separation)
                final_text = _add_section_gaps(final_text, single_doc=False)
                refs = _format_references(all_used_citations, single_doc=False)
                if refs:
                    final_text = f"{final_text}\n\n{refs}"
                return {"content": final_text, "citations": all_used_citations or []}

        # Use vector store retrieval to get top-k relevant chunks (single or no selection)
        try:
            retrieved = await retrieval_store.search(
                query=request.query,
                top_k=8,
                document_ids=request.document_ids
            )
        except Exception as e:
            print(f"Vector search failed, falling back to raw extraction: {str(e)}")
            retrieved = []

        if retrieved:
            # Build concise context from top chunks with source markers
            citations = []
            context_parts = []
            for item in retrieved:
                meta = item.get("metadata", {})
                text = item.get("text", "")
                filename = meta.get("filename", "document")
                page = meta.get("page", "?")
                citations.append({"filename": filename, "page": page})
                context_parts.append(f"[Source: {filename}, page {page}]\n{text}")
            context = "\n\n".join(context_parts)

            # Generate response using the LLM service (accumulate to a single string)
            content_chunks = []
            async for chunk in llm_service.generate_response(
                query=request.query,
                context=context,
                citations=citations
            ):
                content_chunks.append(chunk)
            full_content = "".join(content_chunks).strip()
            if not full_content:
                full_content = "I don't know the answer to that question based on the provided documents."
            # Post-process for readability and references
            single_doc = bool(request.document_ids and len(request.document_ids) == 1)
            pretty = _bold_headings_and_clean(full_content)
            pretty, used = _add_inline_citations(pretty, citations, single_doc)
            refs = _format_references(used, single_doc)
            if refs:
                pretty = f"{pretty}\n\n{refs}"

            return {"content": pretty, "citations": citations}
        else:
            # As a fallback (e.g., empty index), try processing selected files on-the-fly (previous behavior)
            upload_dir = "./data/uploads"
            files_to_process = []
            if os.path.exists(upload_dir):
                for filename in os.listdir(upload_dir):
                    if filename.endswith((".pdf", ".docx", ".txt")):
                        if request.document_ids:
                            file_id = filename.split('_')[0]
                            if file_id in request.document_ids:
                                files_to_process.append(filename)
                        else:
                            files_to_process.append(filename)

            relevant_content = []
            for filename in files_to_process:
                file_path = os.path.join(upload_dir, filename)
                try:
                    # Reuse DocumentProcessor to extract text quickly
                    doc_id = filename.split('_')[0]
                    processed = await document_processor.process_document(file_path, doc_id, filename)
                    chunks = processed.get("chunks", [])
                    metas = processed.get("metadata", [])
                    for chunk, meta in zip(chunks, metas):
                        relevant_content.append((chunk, meta))
                except Exception as e:
                    print(f"Fallback processing failed for {filename}: {str(e)}")

            if relevant_content:
                # Limit to first N chunks
                limited = relevant_content[:8]
                citations = [{"filename": m.get("filename", "document"), "page": m.get("page", "?")} for _, m in limited]
                context = "\n\n".join([f"[Source: {m.get('filename')}, page {m.get('page')}]\n{c}" for c, m in limited])
                content_chunks = []
                async for chunk in llm_service.generate_response(
                    query=request.query,
                    context=context,
                    citations=citations
                ):
                    content_chunks.append(chunk)
                full_content = "".join(content_chunks).strip()
                single_doc = bool(request.document_ids and len(request.document_ids) == 1)
                pretty = _bold_headings_and_clean(full_content)
                pretty, used = _add_inline_citations(pretty, citations, single_doc)
                refs = _format_references(used, single_doc)
                if refs:
                    pretty = f"{pretty}\n\n{refs}"
                return {"content": pretty, "citations": citations}
            else:
                return {"content": "No relevant documents found to answer your question.", "citations": []}
            
    except Exception as e:
        print(f"Error in ask_question: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "content": f"An error occurred while processing your request: {str(e)}",
            "citations": []
        }

@app.get("/documents")
async def list_documents():
    """List all uploaded documents"""
    try:
        # Get all files from upload directory
        upload_dir = "./data/uploads"
        documents = []
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.endswith(('.pdf', '.docx', '.txt')):
                    file_path = os.path.join(upload_dir, filename)
                    file_stat = os.stat(file_path)
                    
                    # Extract document_id from filename (format: uuid_filename)
                    parts = filename.split('_', 1)
                    if len(parts) >= 2:
                        document_id = parts[0]
                        original_filename = parts[1]
                    else:
                        document_id = filename
                        original_filename = filename
                    
                    documents.append({
                        "id": document_id,
                        "document_id": document_id,
                        "filename": original_filename,
                        "upload_date": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "created_at": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                        "pages": 1,  # Placeholder
                        "size": file_stat.st_size
                    })
        
        return documents
    except Exception as e:
        print(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving documents: {str(e)}")

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a specific document"""
    try:
        print(f"=== DELETE REQUEST ===")
        print(f"Document ID: {document_id}")
        
        upload_dir = "./data/uploads"
        deleted_files = []
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.startswith(document_id + "_"):
                    file_path = os.path.join(upload_dir, filename)
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                        print(f"Deleted file: {filename}")
                    except Exception as e:
                        print(f"Error deleting {filename}: {str(e)}")
        
        if deleted_files:
            return {"message": f"Successfully deleted {len(deleted_files)} file(s)", "deleted_files": deleted_files}
        else:
            return {"message": "No files found with that document ID"}
            
    except Exception as e:
        print(f"=== DELETE ERROR ===")
        print(f"Error: {str(e)}")
        return {"error": f"Delete failed: {str(e)}"}

@app.delete("/documents")
async def delete_all_documents():
    """Delete all uploaded documents"""
    try:
        print(f"=== DELETE ALL REQUEST ===")
        
        upload_dir = "./data/uploads"
        deleted_files = []
        
        if os.path.exists(upload_dir):
            for filename in os.listdir(upload_dir):
                if filename.endswith(('.pdf', '.docx', '.txt')):
                    file_path = os.path.join(upload_dir, filename)
                    try:
                        os.remove(file_path)
                        deleted_files.append(filename)
                        print(f"Deleted file: {filename}")
                    except Exception as e:
                        print(f"Error deleting {filename}: {str(e)}")
        
        return {
            "message": f"Successfully deleted {len(deleted_files)} file(s)", 
            "deleted_files": deleted_files
        }
            
    except Exception as e:
        print(f"=== DELETE ALL ERROR ===")
        print(f"Error: {str(e)}")
        return {"error": f"Delete all failed: {str(e)}"}

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Docology API is running", "docs": "/docs"}

@app.get("/test")
async def test():
    """Test endpoint"""
    return {"status": "ok", "message": "Backend is working"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/reindex")
async def reindex_all():
    """Rebuild the vector index from files present in ./data/uploads."""
    upload_dir = "./data/uploads"
    results = []
    if not os.path.exists(upload_dir):
        return {"message": "No uploads directory found", "indexed": results}
    for filename in os.listdir(upload_dir):
        if filename.endswith((".pdf", ".docx", ".txt")):
            file_path = os.path.join(upload_dir, filename)
            info = await _index_saved_file(file_path, filename)
            results.append(info)
    return {"message": "Reindex completed", "indexed": results}

@app.post("/clear_index")
async def clear_index():
    """Clear all vectors from the collection (does not delete uploaded files)."""
    try:
        # Chroma has no direct 'clear', so we can recreate the collection
        # Get all ids and delete
        if vector_store.collection is None:
            return {"message": "Vector store not initialized"}
        all_items = vector_store.collection.get(include=["ids"])
        ids = all_items.get("ids", [])
        if ids:
            vector_store.collection.delete(ids=ids)
        return {"message": f"Cleared {len(ids)} items from index"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    import socket
    
    def is_port_in_use(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    # Try default port 8000, if not available, try 8001, 8002, etc.
    port = 8000
    while is_port_in_use(port):
        print(f"Port {port} is in use, trying next port...")
        port += 1
    
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="127.0.0.1", port=port)
