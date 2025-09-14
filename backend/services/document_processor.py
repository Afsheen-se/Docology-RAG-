import os
import fitz  # PyMuPDF
import docx
from typing import Dict, List
import tiktoken
import re

class DocumentProcessor:
    def __init__(self):
        self.chunk_size = 800
        self.chunk_overlap = 150
        self.encoding = tiktoken.get_encoding("cl100k_base")
    
    async def process_document(self, file_path: str, document_id: str, filename: str) -> Dict:
        """Process document and return chunks with metadata"""
        try:
            # Check if file exists
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            file_extension = os.path.splitext(file_path)[1].lower()
            
            if file_extension == '.pdf':
                return await self._process_pdf(file_path, document_id, filename)
            elif file_extension == '.docx':
                return await self._process_docx(file_path, document_id, filename)
            elif file_extension == '.txt':
                return await self._process_txt(file_path, document_id, filename)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            raise Exception(f"Error processing document: {str(e)}")
    
    async def _process_pdf(self, file_path: str, document_id: str, filename: str) -> Dict:
        """Process PDF document"""
        doc = fitz.open(file_path)
        text_content = []
        page_texts = {}
        
        # Some PDFs are encrypted or contain only images; handle gracefully
        try:
            num_pages = len(doc)
        except Exception:
            num_pages = 0
        
        for page_index in range(num_pages):
            page = doc[page_index]
            page_number = page_index + 1
            extracted = ""
            
            # 1) Default text extraction
            try:
                extracted = page.get_text("text") or ""
            except Exception:
                extracted = ""
            
            # 2) If empty, try layout mode
            if not extracted.strip():
                try:
                    extracted = page.get_text("layout") or ""
                except Exception:
                    pass
            
            # 3) If still empty, try blocks and join
            if not extracted.strip():
                try:
                    blocks = page.get_text("blocks") or []
                    if isinstance(blocks, list):
                        extracted = "\n".join([b[4] for b in blocks if isinstance(b, (tuple, list)) and len(b) > 4 and isinstance(b[4], str)])
                except Exception:
                    pass
            
            # 4) As a fallback, try PyPDF2 (helps on some files)
            if not extracted.strip():
                try:
                    import PyPDF2
                    with open(file_path, 'rb') as fh:
                        reader = PyPDF2.PdfReader(fh)
                        if page_index < len(reader.pages):
                            extracted = reader.pages[page_index].extract_text() or ""
                except Exception:
                    pass

            # 5) Ultimate fallback: OCR the page image if Tesseract is available
            if not extracted.strip():
                try:
                    # Render page to image using PyMuPDF
                    pix = page.get_pixmap(dpi=200)
                    if pix and pix.samples:
                        # Lazy imports to avoid hard dependency if user doesn't need OCR
                        try:
                            from PIL import Image
                            import io
                            import pytesseract
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            # OCR with English as default; users can configure TESSDATA_PREFIX if needed
                            ocr_text = pytesseract.image_to_string(img)
                            if isinstance(ocr_text, str):
                                extracted = ocr_text
                        except ImportError:
                            # OCR not available; skip silently
                            pass
                        except Exception:
                            # Any OCR failure should not break the pipeline
                            pass
                except Exception:
                    # Rendering failure, continue
                    pass
            
            # Record extracted text (may be empty for scanned PDFs)
            text_content.append(extracted)
            page_texts[page_number] = extracted
        
        doc.close()
        
        full_text = "\n".join([t for t in text_content if isinstance(t, str)])
        if not full_text.strip():
            # Return a minimal placeholder so upstream can notify the user clearly
            return {
                "chunks": [
                    "This PDF appears to contain little or no extractable text (it may be scanned images)."
                ],
                "metadata": [{
                    "document_id": document_id,
                    "filename": filename,
                    "page": 1,
                    "chunk_index": 0
                }],
                "pages": num_pages,
                "filename": filename
            }
        
        chunks = self._chunk_text(full_text)
        
        # Add page information to chunks
        chunked_metadata = []
        for chunk in chunks:
            page_num = self._find_page_for_chunk(chunk, page_texts)
            chunked_metadata.append({
                "document_id": document_id,
                "filename": filename,
                "page": page_num,
                "chunk_index": len(chunked_metadata)
            })
        
        return {
            "chunks": chunks,
            "metadata": chunked_metadata,
            "pages": num_pages,
            "filename": filename
        }
    
    async def _process_docx(self, file_path: str, document_id: str, filename: str) -> Dict:
        """Process DOCX document"""
        doc = docx.Document(file_path)
        text_content = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        full_text = "\n".join(text_content)
        chunks = self._chunk_text(full_text)
        
        chunked_metadata = []
        for i, chunk in enumerate(chunks):
            chunked_metadata.append({
                "document_id": document_id,
                "filename": filename,
                "page": "Unknown",  # DOCX doesn't have clear page breaks
                "chunk_index": i
            })
        
        return {
            "chunks": chunks,
            "metadata": chunked_metadata,
            "pages": 1,  # Approximate
            "filename": filename
        }
    
    async def _process_txt(self, file_path: str, document_id: str, filename: str) -> Dict:
        """Process TXT document"""
        with open(file_path, 'r', encoding='utf-8') as file:
            full_text = file.read()
        
        chunks = self._chunk_text(full_text)
        
        chunked_metadata = []
        for i, chunk in enumerate(chunks):
            chunked_metadata.append({
                "document_id": document_id,
                "filename": filename,
                "page": "Unknown",
                "chunk_index": i
            })
        
        return {
            "chunks": chunks,
            "metadata": chunked_metadata,
            "pages": 1,
            "filename": filename
        }
    
    def _chunk_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap"""
        # Tokenize text
        tokens = self.encoding.encode(text)
        
        chunks = []
        start = 0
        
        while start < len(tokens):
            # Get chunk tokens
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            
            # Decode chunk
            chunk_text = self.encoding.decode(chunk_tokens)
            
            # Clean up chunk
            chunk_text = self._clean_text(chunk_text)
            
            if chunk_text.strip():
                chunks.append(chunk_text)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            
            # Prevent infinite loop
            if start >= len(tokens) - self.chunk_overlap:
                break
        
        return chunks
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters that might cause issues
        text = re.sub(r'[^\w\s.,!?;:()\-]', '', text)
        return text.strip()
    
    def _find_page_for_chunk(self, chunk: str, page_texts: Dict[int, str]) -> int:
        """Find which page a chunk belongs to"""
        chunk_words = set(chunk.lower().split())
        
        best_page = 1
        max_overlap = 0
        
        for page_num, page_text in page_texts.items():
            page_words = set(page_text.lower().split())
            overlap = len(chunk_words.intersection(page_words))
            
            if overlap > max_overlap:
                max_overlap = overlap
                best_page = page_num
        
        return best_page
