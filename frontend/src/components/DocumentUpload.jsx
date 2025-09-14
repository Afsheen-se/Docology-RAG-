import React, { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, FileText, AlertCircle, File as FileIcon, AlignLeft } from 'lucide-react'
import { useStore } from '../store/useStore'
import { documentAPI } from '../services/api'

const DocumentUpload = () => {
  const { uploading, setUploading, addDocument, setDocuments } = useStore()

  const onDrop = useCallback(async (acceptedFiles) => {
    if (acceptedFiles.length === 0) return

    setUploading(true)
    
    try {
      // Upload files one by one
      for (const file of acceptedFiles) {
        console.log('Uploading file:', file.name)
        const result = await documentAPI.upload(file)
        console.log('Upload result:', result)
        
        addDocument({
          id: result.document_id,
          filename: result.filename,
          pages: result.pages,
          size: result.size,
          created_at: new Date().toISOString()
        })
      }
      
      // Refresh document list from server
      console.log('Refreshing document list...')
      const documents = await documentAPI.list()
      console.log('Documents from server:', documents)
      setDocuments(documents)
      
    } catch (error) {
      console.error('Upload failed:', error)
      alert('Upload failed. Please try again.')
    } finally {
      setUploading(false)
    }
  }, [setUploading, addDocument, setDocuments])

  // Dedicated dropzones for PDF, DOCX, and TXT
  const pdfDropzone = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'] },
    maxFiles: 5,
    disabled: uploading
  })

  const docxDropzone = useDropzone({
    onDrop,
    accept: { 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
    maxFiles: 5,
    disabled: uploading
  })

  const txtDropzone = useDropzone({
    onDrop,
    accept: { 'text/plain': ['.txt'] },
    maxFiles: 5,
    disabled: uploading
  })

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Documents</h2>

      {/* Three distinct upload cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* PDF */}
        <div
          {...pdfDropzone.getRootProps()}
          className={`rounded-lg p-5 border-2 border-dashed cursor-pointer transition-all ${
            pdfDropzone.isDragActive ? 'border-rose-300 bg-rose-50' : 'border-gray-300 hover:border-gray-400'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Upload PDF documents (.pdf)"
        >
          <input {...pdfDropzone.getInputProps()} />
          <div className="flex flex-col items-center text-center">
            <FileText className="h-10 w-10 text-rose-500 mb-3" />
            <p className="font-medium text-gray-900">PDF</p>
            <p className="text-sm text-gray-600">Drop or click to upload .pdf files</p>
          </div>
        </div>

        {/* DOCX */}
        <div
          {...docxDropzone.getRootProps()}
          className={`rounded-lg p-5 border-2 border-dashed cursor-pointer transition-all ${
            docxDropzone.isDragActive ? 'border-indigo-300 bg-indigo-50' : 'border-gray-300 hover:border-gray-400'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Upload Word documents (.docx)"
        >
          <input {...docxDropzone.getInputProps()} />
          <div className="flex flex-col items-center text-center">
            <FileIcon className="h-10 w-10 text-indigo-500 mb-3" />
            <p className="font-medium text-gray-900">DOCX</p>
            <p className="text-sm text-gray-600">Drop or click to upload .docx files</p>
          </div>
        </div>

        {/* TXT */}
        <div
          {...txtDropzone.getRootProps()}
          className={`rounded-lg p-5 border-2 border-dashed cursor-pointer transition-all ${
            txtDropzone.isDragActive ? 'border-emerald-300 bg-emerald-50' : 'border-gray-300 hover:border-gray-400'
          } ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
          title="Upload Text files (.txt)"
        >
          <input {...txtDropzone.getInputProps()} />
          <div className="flex flex-col items-center text-center">
            <AlignLeft className="h-10 w-10 text-emerald-500 mb-3" />
            <p className="font-medium text-gray-900">TXT</p>
            <p className="text-sm text-gray-600">Drop or click to upload .txt files</p>
          </div>
        </div>
      </div>

      {/* Status / helper */}
      <div className="mt-4 text-center text-sm text-gray-600">
        {uploading ? (
          <div className="inline-flex items-center gap-2">
            <span className="animate-spin rounded-full h-4 w-4 border-2 border-b-transparent border-primary-600"></span>
            Uploading and processing document(s)...
          </div>
        ) : (
          <div className="inline-flex items-center gap-2">
            <Upload className="h-4 w-4 text-gray-400" />
            You can upload up to 5 files at once. Supported: PDF, DOCX, TXT.
          </div>
        )}
      </div>

      {/* Rejection banner across any dropzone */}
      {(pdfDropzone.fileRejections.length > 0 || docxDropzone.fileRejections.length > 0 || txtDropzone.fileRejections.length > 0) && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center">
            <AlertCircle className="h-4 w-4 text-red-500 mr-2" />
            <span className="text-sm text-red-700">
              Some files were rejected. Please upload PDF (.pdf), Word (.docx), or Text (.txt) files only.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}

export default DocumentUpload
