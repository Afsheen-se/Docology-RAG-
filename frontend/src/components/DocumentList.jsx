import React, { useEffect, useState } from 'react'
import { FileText, Check, Clock, File, Trash2, Trash } from 'lucide-react'
import { useStore } from '../store/useStore'
import { documentAPI } from '../services/api'

const DocumentList = () => {
  const { documents, selectedDocuments, setDocuments, setSelectedDocuments } = useStore()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const docs = await documentAPI.list()
      setDocuments(docs)
    } catch (error) {
      console.error('Failed to load documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleDocumentSelection = (documentId) => {
    setSelectedDocuments(
      selectedDocuments.includes(documentId)
        ? selectedDocuments.filter(id => id !== documentId)
        : [...selectedDocuments, documentId]
    )
  }

  const deleteDocument = async (documentId, event) => {
    event.stopPropagation() // Prevent selection toggle
    
    if (window.confirm('Are you sure you want to delete this document?')) {
      try {
        console.log('Deleting document:', documentId)
        await documentAPI.delete(documentId)
        
        // Remove from selected documents if it was selected
        setSelectedDocuments(selectedDocuments.filter(id => id !== documentId))
        
        // Reload documents list
        await loadDocuments()
        
        console.log('Document deleted successfully')
      } catch (error) {
        console.error('Failed to delete document:', error)
        alert('Failed to delete document. Please try again.')
      }
    }
  }

  const deleteAllDocuments = async () => {
    if (window.confirm('Are you sure you want to delete ALL documents? This action cannot be undone.')) {
      try {
        console.log('Deleting all documents...')
        await documentAPI.deleteAll()
        
        // Clear selected documents
        setSelectedDocuments([])
        
        // Reload documents list
        await loadDocuments()
        
        console.log('All documents deleted successfully')
      } catch (error) {
        console.error('Failed to delete all documents:', error)
        alert('Failed to delete all documents. Please try again.')
      }
    }
  }

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
    return (
      <div className="card">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Documents</h2>
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="card min-w-0">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Documents</h2>
        <div className="flex items-center space-x-3">
          <span className="text-sm text-gray-500">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
          </span>
          {documents.length > 0 && (
            <button
              onClick={deleteAllDocuments}
              className="flex items-center space-x-1 px-3 py-1 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-md transition-colors"
              title="Delete all documents"
            >
              <Trash className="h-4 w-4" />
              <span>Delete All</span>
            </button>
          )}
        </div>
      </div>
      
      {documents.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <FileText className="mx-auto h-12 w-12 text-gray-300 mb-4" />
          <p>No documents uploaded yet</p>
          <p className="text-sm">Upload some documents to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc) => (
            <div
              key={doc.id}
              className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                selectedDocuments.includes(doc.id)
                  ? 'border-primary-300 bg-primary-50'
                  : 'border-gray-200 hover:border-gray-300'
              }`}
              onClick={() => toggleDocumentSelection(doc.id)}
            >
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <File className="h-5 w-5 text-gray-400 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <p 
                      className="text-sm font-medium text-gray-900 break-all leading-tight max-w-full"
                      title={doc.filename}
                    >
                      {doc.filename}
                    </p>
                    <div className="flex items-center space-x-4 mt-1 text-xs text-gray-500">
                      <span className="flex items-center">
                        <Clock className="h-3 w-3 mr-1" />
                        {formatDate(doc.created_at)}
                      </span>
                      <span>{doc.pages} pages</span>
                      <span>{formatFileSize(doc.size)}</span>
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  {selectedDocuments.includes(doc.id) && (
                    <Check className="h-5 w-5 text-primary-600" />
                  )}
                  <button
                    onClick={(e) => deleteDocument(doc.id, e)}
                    className="p-1 text-gray-400 hover:text-red-500 transition-colors"
                    title="Delete document"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {selectedDocuments.length > 0 && (
        <div className="mt-4 p-3 bg-primary-50 border border-primary-200 rounded-lg">
          <p className="text-sm text-primary-700">
            {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''} selected for Q&A
          </p>
        </div>
      )}
    </div>
  )
}

export default DocumentList
