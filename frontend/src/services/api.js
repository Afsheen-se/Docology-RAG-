import axios from 'axios'

const API_BASE_URL = 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const documentAPI = {
  upload: async (file) => {
    console.log('Starting upload for file:', file.name, 'Type:', file.type)
    
    const formData = new FormData()
    formData.append('file', file)
    
    console.log('FormData created, sending POST request...')
    
    try {
      const response = await fetch('http://127.0.0.1:8000/upload', {
        method: 'POST',
        body: formData,
        mode: 'cors',
      })
      
      console.log('Upload response status:', response.status)
      console.log('Upload response headers:', response.headers)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('Response error:', errorText)
        throw new Error(`HTTP ${response.status}: ${errorText}`)
      }
      
      const result = await response.json()
      console.log('Upload response data:', result)
      
      if (result.error) {
        throw new Error(result.error)
      }
      
      return result
    } catch (error) {
      console.error('Upload error:', error)
      throw error
    }
  },
  
  list: async () => {
    const response = await fetch('http://127.0.0.1:8000/documents')
    if (!response.ok) {
      throw new Error('Failed to fetch documents')
    }
    return await response.json()
  },
  
  delete: async (documentId) => {
    console.log('Deleting document:', documentId)
    const response = await fetch(`http://127.0.0.1:8000/documents/${documentId}`, {
      method: 'DELETE',
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Delete failed: ${response.status} - ${errorText}`)
    }
    
    return await response.json()
  },
  
  deleteAll: async () => {
    console.log('Deleting all documents...')
    const response = await fetch('http://127.0.0.1:8000/documents', {
      method: 'DELETE',
    })
    
    if (!response.ok) {
      const errorText = await response.text()
      throw new Error(`Delete all failed: ${response.status} - ${errorText}`)
    }
    
    return await response.json()
  },
}

export const chatAPI = {
  ask: async (query, documentIds = null) => {
    const response = await fetch('http://127.0.0.1:8000/ask', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        document_ids: documentIds,
      }),
    })
    
    if (!response.ok) {
      throw new Error('Failed to send message')
    }
    
    return response
  },
}

export default api
