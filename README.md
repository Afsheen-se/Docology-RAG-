# Docology - RAG Document Q&A System

A production-ready MVP for document question-answering using Retrieval-Augmented Generation (RAG) with Gemini 1.5 Pro, ChromaDB, and local embeddings.

## Features

- **Document Upload**: Support for PDF, DOCX, and TXT files
- **Intelligent Chunking**: 800-token chunks with 150-token overlap
- **Local Embeddings**: Using sentence-transformers/all-MiniLM-L6-v2
- **Vector Storage**: ChromaDB with persistent storage
- **AI-Powered Q&A**: Gemini 1.5 Pro integration with clean, formatted responses
- **Citation Support**: Inline citations with page-only (single doc) or filename+page (multi-doc), plus a REFERENCES block
- **Modern UI**: React + Vite + Tailwind CSS with drag-drop interface
- **Document Selection**: Choose specific documents for Q&A scope

## Architecture

### Backend (FastAPI)
- **Document Processing**: PDF/DOCX/TXT parsing and chunking
- **Vector Store**: ChromaDB with MMR (Maximal Marginal Relevance) search
- **LLM Integration**: Google Gemini 1.5 Pro API (default)
- **Responses**: Formatted text (bullets, bold headings, inline citations)
- **CORS Support**: Configured for frontend integration

### Frontend (React + Vite)
- **Document Upload**: Drag-and-drop interface with file validation and three dedicated upload cards (PDF, DOCX, TXT)
- **Document Management**: List, select, and manage uploaded documents
- **Chat Interface**: Real-time Q&A with streaming responses
- **Citation Display**: Inline citation chips with source references
- **Responsive Design**: Mobile-friendly Tailwind CSS styling

## Prerequisites

- Python 3.13+
- Node.js 16+
- Google AI API Key (free tier)

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd docology
```

### 2. Environment Configuration

Copy the example environment file and add your Google API key:

```bash
cp env.example .env
```

Edit `.env` and add your Google API key:

```env
GOOGLE_API_KEY=your_google_api_key_here
GEMINI_MODEL=gemini-1.5-pro-latest
CHROMA_DIR=./data/persisted
UPLOAD_DIR=./data/uploads
# Optional: switch retrieval backend to LangChain's Chroma wrapper
USE_LANGCHAIN=false
```

**Get your Google API key:**
1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create a new API key
3. Copy the key to your `.env` file

### 3. Run Backend

```bash
python run_backend.py
```

The backend will:
- Create a virtual environment
- Install Python dependencies
- Start the FastAPI server on http://localhost:8000
- API documentation available at http://localhost:8000/docs

### 4. Run Frontend (New Terminal)

```bash
python run_frontend.py
```

The frontend will:
- Install Node.js dependencies
- Start the Vite development server on http://localhost:5173

### 5. Access the Application

Open your browser and go to http://localhost:5173

## Manual Setup (Alternative)

### Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

## Usage

### 1. Upload Documents
- Drag and drop PDF, DOCX, or TXT files onto the upload area
- Documents are automatically processed and chunked
- Processing status is shown in real-time

### 2. Select Documents
- Choose which documents to include in your Q&A session
- Select all documents or specific ones
- Selected documents are highlighted

### 3. Ask Questions
- Type your question in the chat interface
- Press Enter or click Send
- Get formatted responses with inline citations
- Citations show page only (single selected doc) or filename + page (multiple docs)

### 4. View Results
- Answers are generated in real-time
- Citations appear as chips below responses
- Click citations to see source information

## API Endpoints

### Document Management
- `POST /upload` - Upload and process documents
- `GET /documents` - List all uploaded documents

- `POST /ask` - Ask questions and receive formatted JSON response `{ content, citations }`
- `POST /reindex` - Rebuild the vector index from files in `./data/uploads`
- `POST /clear_index` - Clear all vectors from the collection (does not delete files)
- `GET /health` - Health check endpoint

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_API_KEY` | Google AI API key | Required |
| `GEMINI_MODEL` | Gemini model to use | `gemini-1.5-pro-latest` |
| `CHROMA_DIR` | ChromaDB storage path | `./data/persisted` |
| `UPLOAD_DIR` | Upload storage path | `./data/uploads` |
| `USE_LANGCHAIN` | Use LangChain Chroma wrapper for retrieval | `false` |

### Document Processing
- **Chunk Size**: 800 tokens
- **Chunk Overlap**: 150 tokens
- **Embedding Model**: sentence-transformers/all-MiniLM-L6-v2
- **Vector Search**: Top 8 results with MMR
- **OCR Fallback (Optional)**: For scanned PDFs, install Tesseract OCR and Python deps (`pillow`, `pytesseract`).

## File Structure

```
docology/
├── backend/
│   ├── main.py                 # FastAPI application
│   ├── models/                 # Pydantic models
│   ├── services/               # Business logic
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/         # React components
│   │   ├── services/           # API services
│   │   └── store/              # State management
│   ├── package.json            # Node.js dependencies
│   └── vite.config.js          # Vite configuration
├── data/                       # Data storage (created automatically)
├── .env                        # Environment variables
├── run_backend.py              # Backend runner script
├── run_frontend.py             # Frontend runner script
└── README.md                   # This file
```

## Troubleshooting

### Common Issues

1. **Google API Key Error**
   - Ensure your API key is valid and has Gemini access
   - Check the `.env` file is in the project root

2. **Port Already in Use**
   - Backend: Change port in `run_backend.py` or kill process on port 8000
   - Frontend: Change port in `vite.config.js` or kill process on port 5173

3. **Document Upload Fails**
   - Check file format (PDF, DOCX, TXT only)
   - Ensure file is not corrupted
   - Check upload directory permissions

4. **ChromaDB Issues**
   - Delete `data/persisted` directory to reset
   - Check disk space and permissions

### Performance Tips

- Use SSD storage for better ChromaDB performance
- Limit document size for faster processing
- Close unused browser tabs to free memory

## Development

### Adding New Document Types

1. Add parser in `backend/services/document_processor.py`
2. Update file validation in `frontend/src/components/DocumentUpload.jsx`
3. Test with sample files

### Customizing UI

- Modify Tailwind classes in components
- Update color scheme in `tailwind.config.js`
- Add new components in `frontend/src/components/`

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the API documentation at http://localhost:8000/docs
3. Check browser console for frontend errors
4. Check backend logs for server errors

---

**Note**: This is a free-tier implementation using only open-source and free services. No paid APIs or services are required.
