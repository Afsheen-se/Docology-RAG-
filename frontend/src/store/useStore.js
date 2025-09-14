import { create } from 'zustand'

const useStore = create((set, get) => ({
  // Document state
  documents: [],
  selectedDocuments: [],
  uploading: false,
  
  // Chat state
  messages: [],
  isStreaming: false,
  currentQuery: '',
  
  // Actions
  setDocuments: (documents) => set({ documents }),
  
  addDocument: (document) => set((state) => ({
    documents: [...state.documents, document]
  })),
  
  setSelectedDocuments: (documentIds) => set({ selectedDocuments: documentIds }),
  
  setUploading: (uploading) => set({ uploading }),
  
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  
  setMessages: (messages) => set({ messages }),
  
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  
  setCurrentQuery: (query) => set({ currentQuery: query }),
  
  clearChat: () => set({ messages: [], currentQuery: '' }),
}))

export { useStore }
