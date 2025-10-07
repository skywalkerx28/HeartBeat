'use client'

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { XMarkIcon, PaperAirplaneIcon } from '@heroicons/react/24/outline'
import { api } from '@/lib/api'
import { ChatMessage } from '@/components/hockey-specific/ChatMessage'
import { TypingIndicator } from '@/components/hockey-specific/TypingIndicator'

interface Message {
  id: string
  role: 'user' | 'stanley'
  content: string
  timestamp: Date
  analytics?: any[]
}

interface GlobalAISidebarProps {
  isOpen: boolean
  onClose: () => void
  currentPage?: string
}

export function GlobalAISidebar({ isOpen, onClose, currentPage = 'unknown' }: GlobalAISidebarProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentToolStatus, setCurrentToolStatus] = useState<string | undefined>(undefined)
  const [sidebarWidth, setSidebarWidth] = useState(420) // Default width
  const [isResizing, setIsResizing] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const sidebarRef = useRef<HTMLDivElement>(null)

  // Min and max width constraints
  const MIN_WIDTH = 320
  const MAX_WIDTH = 800

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isTyping])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  // Prevent scroll propagation to main page when scrolling inside sidebar
  const handleWheel = (e: React.WheelEvent) => {
    e.stopPropagation()
  }

  // Resize handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isResizing) return
      
      const newWidth = window.innerWidth - e.clientX
      
      // Apply constraints
      if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
        setSidebarWidth(newWidth)
      }
    }

    const handleMouseUp = () => {
      if (isResizing) {
        setIsResizing(false)
        // Persist width to localStorage
        localStorage.setItem('stanley_sidebar_width', sidebarWidth.toString())
      }
    }

    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove)
      document.addEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = 'ew-resize'
      document.body.style.userSelect = 'none'
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
    }
  }, [isResizing, sidebarWidth, MIN_WIDTH, MAX_WIDTH])

  // Load saved width on mount
  useEffect(() => {
    const savedWidth = localStorage.getItem('stanley_sidebar_width')
    if (savedWidth) {
      const width = parseInt(savedWidth, 10)
      if (width >= MIN_WIDTH && width <= MAX_WIDTH) {
        setSidebarWidth(width)
      }
    }
  }, [])

  const getPageContext = () => {
    const contexts: Record<string, string> = {
      'analytics': 'User is viewing the Analytics dashboard',
      'schedule': 'User is viewing the NHL Schedule page',
      'dashboard': 'User is viewing the main Dashboard',
      'scouting': 'User is viewing Scouting reports',
      'video': 'User is viewing Video analysis'
    }
    return contexts[currentPage] || `User is on the ${currentPage} page`
  }

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isTyping) return

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, newMessage])
    setInputValue('')
    setIsTyping(true)
    setCurrentToolStatus('reasoning')

    try {
      await new Promise(resolve => setTimeout(resolve, 500))
      setCurrentToolStatus('parquet_query')
      
      const queryResponse = await api.sendQuery({ 
        query: newMessage.content,
        context: getPageContext()
      })
      
      setCurrentToolStatus('synthesizing')
      await new Promise(resolve => setTimeout(resolve, 300))
      
      const stanleyResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'stanley',
        content: queryResponse.response,
        timestamp: new Date(),
        analytics: queryResponse.analytics.length > 0 ? queryResponse.analytics.map(item => ({
          type: (item.type as any) ?? 'stat',
          title: item.title,
          data: item.data,
          clips: (item as any).clips || []
        })) : undefined
      }
      
      setMessages(prev => [...prev, stanleyResponse])
      setIsTyping(false)
      setCurrentToolStatus(undefined)
    } catch (error) {
      console.error('Error querying STANLEY:', error)
      
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'stanley',
        content: 'System error: Unable to process query. Please verify authentication and try again.',
        timestamp: new Date()
      }
      
      setMessages(prev => [...prev, errorResponse])
      setIsTyping(false)
      setCurrentToolStatus(undefined)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion)
    inputRef.current?.focus()
  }

  // Smart suggestions based on current page - top 3 only
  const getContextualSuggestions = () => {
    const pageSuggestions: Record<string, string[]> = {
      'analytics': [
        "Explain these metrics",
        "Show top performers this season",
        "Compare with league average"
      ],
      'schedule': [
        "Who's our next opponent?",
        "Show upcoming matchups",
        "Analyze recent performance trends"
      ],
      'dashboard': [
        "Latest team statistics",
        "Compare Caufield with Suzuki",
        "Show power play efficiency"
      ],
      'page': [
        "Analyze Caufield's performance",
        "Compare players across teams",
        "Show matchup vs Bruins"
      ]
    }

    return pageSuggestions[currentPage] || pageSuggestions['page']
  }

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Sidebar - Glass with subtle blur */}
          <motion.div
            ref={sidebarRef}
            initial={{ x: '100%' }}
            animate={{ x: 0, width: sidebarWidth }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 30, stiffness: 300 }}
            style={{ width: sidebarWidth }}
            onWheel={handleWheel}
            className="fixed right-0 top-0 bottom-0 
                     bg-black/15 backdrop-blur-sm
                     border-l border-white/10
                     shadow-[0_0_40px_0_rgba(0,0,0,0.3)]
                     z-50 flex flex-col overflow-hidden"
          >
            {/* Resize Handle - Glass theme */}
            <div
              onMouseDown={handleMouseDown}
              className={`
                absolute left-0 top-0 bottom-0 w-1
                hover:bg-white/10
                cursor-ew-resize
                transition-all duration-150
                group
                ${isResizing ? 'bg-red-500/50' : 'bg-transparent'}
              `}
              title="Drag to resize"
            >
              {/* Subtle visual indicator on hover */}
              <div className="absolute left-0 top-1/2 -translate-y-1/2 w-full h-12 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                <div className="w-0.5 h-6 bg-red-500/80 rounded-full shadow-lg shadow-red-500/50" />
              </div>
            </div>
            {/* Header - Glass transparency */}
            <div className="flex items-center justify-between h-16 px-4 border-b border-white/10 bg-transparent">
              <div className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse shadow-lg shadow-red-500/50" />
                <h2 className="text-base font-military-display text-white whitespace-nowrap tracking-wider drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]">
                  STANLEY
                </h2>
              </div>
              
              <button
                onClick={onClose}
                className="p-1.5 rounded-md text-gray-500 hover:text-white hover:bg-white/5 transition-colors"
              >
                <XMarkIcon className="w-4 h-4" />
              </button>
            </div>

            {/* Messages Area - Black glass */}
            <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">

              {messages.map((message) => (
                <ChatMessage
                  key={message.id}
                  message={message}
                />
              ))}

              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                >
                  <TypingIndicator currentTool={currentToolStatus} />
                </motion.div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Floating Suggestions - On glass background */}
            {messages.length === 0 && !inputValue && (
              <div className="px-4 pb-3">
                <div className="space-y-1">
                  {getContextualSuggestions().map((suggestion, index) => (
                    <motion.button
                      key={index}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.1, duration: 0.3 }}
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="w-full text-left px-3 py-2
                               text-gray-300 hover:text-white hover:bg-black/30
                               text-sm font-military-chat
                               rounded-md
                               transition-all duration-200
                               group"
                    >
                      <div className="flex items-center justify-between">
                        <span className="transition-colors drop-shadow-[0_2px_6px_rgba(0,0,0,0.9)]">
                          {suggestion}
                        </span>
                        <svg 
                          className="w-3.5 h-3.5 text-transparent group-hover:text-red-500 transition-all group-hover:translate-x-0.5 drop-shadow-lg" 
                          fill="none" 
                          viewBox="0 0 24 24" 
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
                        </svg>
                      </div>
                    </motion.button>
                  ))}
                </div>
              </div>
            )}

            {/* Input Field - Glass transparency */}
            <div className="px-4 pb-4">
              <div className="relative flex items-center bg-white/5 backdrop-blur-sm border border-white/10 rounded-lg shadow-xl shadow-white/5 overflow-hidden hover:border-white/20 transition-colors">
                {/* Text input */}
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder=""
                  className="flex-1 bg-transparent px-4 py-3.5 text-white placeholder-gray-500 text-sm font-military-chat focus:outline-none"
                  disabled={isTyping}
                />

                {/* Send button */}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isTyping}
                  className="px-4 py-3.5 text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <PaperAirplaneIcon className="w-5 h-5" />
                </button>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

