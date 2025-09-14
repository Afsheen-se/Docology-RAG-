import React, { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { useStore } from '../store/useStore'
import { chatAPI } from '../services/api'

const ChatInterface = () => {
  const { 
    messages, 
    isStreaming, 
    currentQuery, 
    selectedDocuments,
    addMessage, 
    setIsStreaming, 
    setCurrentQuery 
  } = useStore()
  
  const [inputValue, setInputValue] = useState('')
  const messagesEndRef = useRef(null)
  const abortControllerRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!inputValue.trim() || isStreaming) return

    const query = inputValue.trim()
    setInputValue('')
    setCurrentQuery(query)

    // Add user message
    addMessage({
      id: Date.now(),
      type: 'user',
      content: query,
      timestamp: new Date()
    })

    // Add empty assistant message for streaming
    const assistantMessageId = Date.now() + 1
    addMessage({
      id: assistantMessageId,
      type: 'assistant',
      content: '',
      citations: [],
      timestamp: new Date()
    })

    setIsStreaming(true)

    try {
      console.log('Sending chat request...')
      
      const response = await chatAPI.ask(
        query, 
        selectedDocuments.length > 0 ? selectedDocuments : null
      )

      console.log('Chat response:', response)

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      console.log('Chat data:', data)

      // Update the assistant message with the response
      addMessage({
        id: assistantMessageId,
        type: 'assistant',
        content: data.content || data.message || 'No response received',
        citations: data.citations || [],
        timestamp: new Date()
      })

    } catch (error) {
      if (error.name !== 'AbortError') {
        console.error('Chat error:', error)
        addMessage({
          id: Date.now() + 2,
          type: 'error',
          content: 'Sorry, I encountered an error. Please try again.',
          timestamp: new Date()
        })
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
  }

  return (
    <div className="card h-[600px] flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Chat</h2>
        {selectedDocuments.length > 0 && (
          <span className="text-sm text-gray-500">
            Searching {selectedDocuments.length} document{selectedDocuments.length !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            <Bot className="mx-auto h-12 w-12 text-gray-300 mb-4" />
            <p>Ask a question about your documents</p>
            <p className="text-sm">Upload documents and select them to get started</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-3 ${
                  message.type === 'user'
                    ? 'bg-primary-600 text-white'
                    : message.type === 'error'
                    ? 'bg-red-50 text-red-700 border border-red-200'
                    : 'bg-gray-100 text-gray-900'
                }`}
              >
                <div className="flex items-start space-x-2">
                  {message.type !== 'user' && (
                    <Bot className="h-4 w-4 mt-0.5 flex-shrink-0" />
                  )}
                  <div className="flex-1">
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    {message.citations && message.citations.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {message.citations.map((citation, index) => (
                          <span
                            key={index}
                            className="citation-chip"
                            title={citation.filename}
                          >
                            {citation.filename.length > 30 
                              ? citation.filename.substring(0, 30) + '...' 
                              : citation.filename}, p. {citation.page}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="flex space-x-2">
        <div className="flex-1 relative">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about your documents..."
            className="input-field resize-none h-12 pr-12"
            rows={1}
            disabled={isStreaming}
          />
          {isStreaming && (
            <button
              type="button"
              onClick={stopGeneration}
              className="absolute right-2 top-2 p-1 text-gray-400 hover:text-gray-600"
            >
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            </button>
          )}
        </div>
        
        <button
          type="submit"
          disabled={!inputValue.trim() || isStreaming}
          className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed px-4"
        >
          {isStreaming ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </button>
      </form>
    </div>
  )
}

export default ChatInterface
