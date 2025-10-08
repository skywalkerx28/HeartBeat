'use client'

import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { PaperAirplaneIcon, MicrophoneIcon, ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline'
import { ChatMessage } from './ChatMessage'
import { TypingIndicator } from './TypingIndicator'
import { api } from '../../lib/api'
import { useRouter, useSearchParams } from 'next/navigation'

interface Message {
  id: string
  role: 'user' | 'stanley'
  content: string
  timestamp: Date
  analytics?: AnalyticsData[]
}

interface ClipData {
  clip_id: string
  title: string
  player_name: string
  game_info: string
  event_type: string
  description: string
  file_url: string
  thumbnail_url: string
  duration: number
  relevance_score?: number
}

interface AnalyticsData {
  type: 'stat' | 'chart' | 'table' | 'clips'
  title: string
  data: any
  clips?: ClipData[]
}

type AgentMode = 'tactical' | 'statistical' | 'strategic' | 'predictive'

const AGENT_MODES: { id: AgentMode; label: string; description: string }[] = [
  { id: 'tactical', label: 'Tactical', description: 'Real-time game analysis and player deployment strategies' },
  { id: 'statistical', label: 'Statistical', description: 'Deep dive into player stats and historical performance' },
  { id: 'strategic', label: 'Strategic', description: 'Game planning, matchups, and tactical recommendations' },
  { id: 'predictive', label: 'Predictive', description: 'AI-powered predictions and expected outcomes' },
]

export function MilitaryChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentToolStatus, setCurrentToolStatus] = useState<string | undefined>(undefined)
  const [selectedMode, setSelectedMode] = useState<AgentMode>('tactical')
  const [showModeSelector, setShowModeSelector] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const modeSelectorRef = useRef<HTMLDivElement>(null)
  const router = useRouter()
  const searchParams = useSearchParams()
  const [conversationId, setConversationId] = useState<string | null>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Initialize or switch conversations based on URL
  useEffect(() => {
    const init = async () => {
      const existing = searchParams?.get('conversation_id')
      
      if (existing) {
        // Load existing conversation
        setConversationId(existing)
        try {
          const conv = await api.getConversation(existing)
          const msgs = conv.conversation.messages || []
          const hydrated: Message[] = msgs.slice(-50).map((m, idx) => ({
            id: `${existing}_${idx}`,
            role: m.role === 'user' ? 'user' : 'stanley',
            content: m.text,
            timestamp: new Date()
          }))
          setMessages(hydrated)
        } catch (e) {
          console.error('Failed to load conversation', e)
          setMessages([])
        }
        return
      }
      
      // No conversation_id in URL - create new one
      try {
        const res = await api.newConversation()
        const id = res.conversation_id
        setConversationId(id)
        setMessages([])
        const sp = new URLSearchParams(Array.from(searchParams?.entries() || []))
        sp.set('conversation_id', id)
        router.replace(`/chat?${sp.toString()}`)
      } catch (e) {
        console.error('Failed to create conversation', e)
      }
    }
    
    init()
  }, [searchParams, router])

  // Close mode selector when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (modeSelectorRef.current && !modeSelectorRef.current.contains(event.target as Node)) {
        setShowModeSelector(false)
      }
    }

    if (showModeSelector) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [showModeSelector])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || !conversationId) return

    const newMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputValue.trim(),
      timestamp: new Date(),
    }

    setMessages(prev => [...prev, newMessage])
    setInputValue('')
    setIsTyping(true)
    setCurrentToolStatus('reasoning')

    // Call real API for Stanley's response
    try {
      // Show AI reasoning phase
      await new Promise(resolve => setTimeout(resolve, 500))
      setCurrentToolStatus('parquet_query')
      
      const queryResponse = await api.sendQuery({ query: newMessage.content, conversation_id: conversationId })
      
      // Show synthesis phase
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
      console.error('Query error:', error)
      
      // Fallback response on error
      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'stanley',
        content: "I apologize, but I'm experiencing technical difficulties. Please check your connection and try again.",
        timestamp: new Date(),
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

  return (
    <div className="min-h-screen bg-gray-950 relative overflow-hidden">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Radial gradient overlay */}
      <div className="absolute inset-0 bg-gradient-radial from-red-600/5 via-transparent to-transparent opacity-30" />

      {/* Main content container */}
      <div className="relative z-10 flex flex-col h-screen">
        {/* Status indicator - Top Left Corner */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, type: "spring", damping: 20 }}
          className="absolute top-6 left-6 z-20"
        >
          <div className="flex items-center space-x-3 bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg px-4 py-2 shadow-xl shadow-white/5">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
              <span className="text-xs font-military-display text-red-400 tracking-wider">STANLEY AI</span>
            </div>
            <div className="w-px h-4 bg-white/10"></div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-military-display text-white tracking-wider uppercase">
                {AGENT_MODES.find(m => m.id === selectedMode)?.label}
              </span>
            </div>
          </div>
        </motion.div>

        {/* Header - Matching pulse, scores, analytics pages */}
        <div className="pt-8 pb-6">
          <div className="py-2 text-center">
            <h1 className="text-3xl font-military-display text-white tracking-wider">
              HeartBeat
            </h1>
          </div>
        </div>

        {/* Chat messages area */}
        <div className="flex-1 overflow-y-auto px-6 pb-32">
          <div className="max-w-3xl mx-auto py-8">
            
            <AnimatePresence>
              {messages.map((message) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                >
                  <ChatMessage message={message} />
                </motion.div>
              ))}
            </AnimatePresence>

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
        </div>

        {/* Enhanced input area - OpenAI style */}
        <div className="px-6 pb-8 border-t border-white/5">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              {/* Mode selector dropdown */}
              <AnimatePresence>
                {showModeSelector && (
                  <motion.div
                    ref={modeSelectorRef}
                    initial={{ opacity: 0, y: 10, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    transition={{ duration: 0.2 }}
                    className="absolute bottom-full left-0 mb-2 w-80 bg-black/90 backdrop-blur-xl border border-white/20 rounded-lg shadow-2xl shadow-white/10 overflow-hidden"
                  >
                    <div className="p-2">
                      {AGENT_MODES.map((mode) => (
                        <button
                          key={mode.id}
                          onClick={() => {
                            setSelectedMode(mode.id)
                            setShowModeSelector(false)
                          }}
                          className={`w-full text-left px-4 py-3 rounded-lg transition-all duration-200 ${
                            selectedMode === mode.id
                              ? 'bg-red-600/20 border border-red-600/30'
                              : 'hover:bg-white/5 border border-transparent'
                          }`}
                        >
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-military-display text-white tracking-wider">
                              {mode.label}
                            </span>
                            {selectedMode === mode.id && (
                              <div className="w-2 h-2 bg-red-600 rounded-full"></div>
                            )}
                          </div>
                          <p className="text-xs text-gray-400 font-military-chat">
                            {mode.description}
                          </p>
                        </button>
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Input container */}
              <div className="relative flex items-center bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg shadow-xl shadow-white/5 overflow-hidden hover:border-white/20 transition-colors">
                {/* Mode selector button */}
                <button
                  onClick={() => setShowModeSelector(!showModeSelector)}
                  className="flex items-center space-x-2 px-4 py-4 border-r border-white/10 hover:bg-white/5 transition-colors group"
                  disabled={isTyping}
                >
                  <div className="w-2 h-2 bg-red-600 rounded-full transition-colors"></div>
                  <span className="text-sm font-military-display text-white tracking-wider hidden sm:inline">
                    {AGENT_MODES.find(m => m.id === selectedMode)?.label}
                  </span>
                  {showModeSelector ? (
                    <ChevronUpIcon className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                  ) : (
                    <ChevronDownIcon className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" />
                  )}
                </button>

                {/* Text input */}
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyPress={handleKeyPress}
                  placeholder="Ask Stanley anything about hockey analytics..."
                  className="flex-1 bg-transparent px-4 py-4 text-white placeholder-gray-500 text-sm font-military-chat focus:outline-none"
                  disabled={isTyping}
                />

                {/* Send button */}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim() || isTyping}
                  className="px-4 py-4 text-gray-400 hover:text-white hover:bg-white/5 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <PaperAirplaneIcon className="w-5 h-5" />
                </button>

                {/* Microphone button (optional - future feature) */}
                <button
                  className="px-4 py-4 border-l border-white/10 text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                  disabled={isTyping}
                  title="Voice input (coming soon)"
                >
                  <MicrophoneIcon className="w-5 h-5" />
                </button>
              </div>
            </div>
            
            {/* Status footer */}
            <div className="flex items-center justify-center mt-3 text-xs text-gray-500">
              <div className="flex items-center space-x-4">
                <span className="font-military-display">SECURE CONNECTION</span>
                <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                <span className="font-military-display">STANLEY AI v2.1</span>
                <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                <span className="font-military-display">HEARTBEAT ENGINE</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
