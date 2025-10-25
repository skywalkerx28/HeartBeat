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

type AgentMode = 'general' | 'video' | 'financial' | 'fast' | 'report'

// Map UI modes to backend modes configured in orchestrator/config/modes.py
const BACKEND_MODE_MAP: Record<AgentMode, string> = {
  general: 'general',
  video: 'visual_analysis',
  financial: 'contract_finance',
  fast: 'fast',
  report: 'report',
}

const AGENT_MODES: { id: AgentMode; label: string; description: string }[] = [
  { id: 'general', label: 'General', description: 'Analytics across tools' },
  { id: 'video', label: 'Video', description: 'Clips and visual analysis' },
  { id: 'financial', label: 'Financial', description: 'Contracts and cap space' },
  { id: 'fast', label: 'Fast', description: 'Quick responses' },
  { id: 'report', label: 'Report', description: 'Pre-scout analysis' },
]

export function MilitaryChatInterface() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isTyping, setIsTyping] = useState(false)
  const [currentToolStatus, setCurrentToolStatus] = useState<string | undefined>(undefined)
  const [selectedMode, setSelectedMode] = useState<AgentMode>('general')
  const [showModeSelector, setShowModeSelector] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
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

  // Auto-resize textarea as user types
  useEffect(() => {
    const textarea = inputRef.current
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [inputValue])

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

    // Proactively guide the user on very short/ambiguous inputs
    const text = newMessage.content.trim()
    const lower = text.toLowerCase()
    const isOnlyPunctuation = /^[\s?!.,;:\-_'"()]+$/.test(text)
    const shortGreeting = ['hi', 'hey', 'yo', 'k', 'ok', 'sup', 'hello'].includes(lower)
    if (text.length < 5 || isOnlyPunctuation || shortGreeting) {
      const clarify: Message = {
        id: (Date.now() + 2).toString(),
        role: 'stanley',
        content: "I want to help—could you add a bit more detail? For example: 'Compare two players over the last 10 games', 'Show a team's power-play this season', or 'Find clips of a player's goals vs an opponent'.",
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, clarify])
      return
    }

    setIsTyping(true)
    setCurrentToolStatus('reasoning')

    // Call real API for Stanley's response
    try {
      // Show AI reasoning phase
      await new Promise(resolve => setTimeout(resolve, 500))
      setCurrentToolStatus('parquet_query')
      
      const backendMode = BACKEND_MODE_MAP[selectedMode]
      const queryResponse = await api.sendQuery({ query: newMessage.content, conversation_id: conversationId, mode: backendMode })
      
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
      // Provide professional, actionable feedback instead of a vague error
      let friendly: string
      if (error instanceof Error) {
        const msg = error.message || ''
        if (/clarification|too short|ambiguous|at least\s*\d+\s*characters|String should have at least/i.test(msg)) {
          friendly = "I didn't catch that. Could you add a few more words? For example: 'Show a team's xGF over the last 10 games' or 'Retrieve clips of a player's goals vs a team'."
        } else if (/Authentication required|401/i.test(msg)) {
          friendly = 'Your session has expired. Please sign in and try again.'
        } else if (/NetworkError|Failed to fetch|ECONN|timeout|CORS|fetch.*failed/i.test(msg)) {
          friendly = "I couldn't reach the server. Please check your connection and try again."
        } else {
          friendly = msg
        }
      } else {
        friendly = "I couldn't complete that request. Please try again."
      }

      const errorResponse: Message = {
        id: (Date.now() + 1).toString(),
        role: 'stanley',
        content: friendly,
        timestamp: new Date(),
      }

      setMessages(prev => [...prev, errorResponse])
      setIsTyping(false)
      setCurrentToolStatus(undefined)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter without Shift sends the message
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
    // Shift+Enter adds a new line (default behavior)
  }

  const hasMessages = messages.length > 0

  return (
    <div className="min-h-screen bg-gray-50 relative dark:bg-gray-950">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-30 pointer-events-none dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(156, 163, 175, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(156, 163, 175, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>
      
      {/* Dark mode grid overlay */}
      <div className="absolute inset-0 opacity-0 pointer-events-none dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Radial gradient overlay */}
      <div className="absolute inset-0 bg-gradient-radial from-red-500/5 via-transparent to-transparent opacity-20 pointer-events-none dark:from-red-600/5 dark:opacity-30" />

      {/* Pulse animation intentionally only on Analytics page */}

      {/* Main content container */}
      <div className="relative z-10 flex flex-col min-h-screen">
        {/* Status indicator - Top Left Corner */}
        {/* Header - Always visible */}
        <div className="pt-3 pb-4">
          <div className="py-1 text-center">
            <h1 className="text-xl font-military-display text-gray-900 tracking-wider dark:text-white">
              HeartBeat
            </h1>
          </div>
        </div>

        {/* Conditional layout: Landing page vs Chat interface */}
        <AnimatePresence mode="wait">
          {!hasMessages ? (
            // LANDING PAGE - Centered like Grok
            <motion.div 
              key="landing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col items-center justify-center px-4"
            >
            <div className="w-full max-w-3xl mx-auto">

              {/* Centered Search Input */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.3, type: "spring", damping: 20 }}
                className="mb-8"
              >
                <div className="relative">
                  {/* Mode selector dropdown */}
                  <AnimatePresence>
                    {showModeSelector && (
                      <motion.div
                        ref={modeSelectorRef}
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        className="absolute bottom-full left-0 mb-2 w-48 bg-white/95 backdrop-blur-xl border border-gray-200 rounded-lg shadow-2xl shadow-gray-300/50 overflow-hidden dark:bg-black/95 dark:border-white/10 dark:shadow-black/30"
                      >
                        <div className="p-1">
                          {AGENT_MODES.map((mode) => (
                            <button
                              key={mode.id}
                              onClick={() => {
                                setSelectedMode(mode.id)
                                setShowModeSelector(false)
                              }}
                              className={`w-full text-left px-3 py-2 rounded-md transition-all duration-150 ${
                                selectedMode === mode.id
                                  ? 'bg-red-600/25 dark:bg-red-600/20'
                                  : 'hover:bg-gray-100 dark:hover:bg-white/5'
                              }`}
                            >
                              <div className="flex items-center justify-between mb-0.5">
                                <span className="text-xs font-military-display text-gray-900 tracking-wider dark:text-white">
                                  {mode.label}
                                </span>
                                {selectedMode === mode.id && (
                                  <div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div>
                                )}
                              </div>
                              <p className="text-[10px] text-gray-600 leading-tight dark:text-gray-500">
                                {mode.description}
                              </p>
                            </button>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Enhanced centered input - ChatGPT Codex Style */}
                  <div className="relative rounded-2xl bg-white/80 backdrop-blur-md border border-gray-200 shadow-2xl shadow-gray-300/30 hover:border-gray-300 transition-all duration-200 dark:bg-black/20 dark:border-white/5 dark:shadow-black/20 dark:hover:border-white/10">
                    <div className="flex items-center gap-2 px-3 py-2">
                      {/* Mode selector button (left) */}
                      <button
                        onClick={() => setShowModeSelector(!showModeSelector)}
                        className="flex-shrink-0 flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors group dark:hover:bg-white/10"
                        disabled={isTyping}
                      >
                        <div className="w-2.5 h-2.5 bg-red-600 rounded-full transition-all group-hover:scale-110"></div>
                        <span className="text-sm font-military-display text-gray-900 tracking-wider hidden sm:inline dark:text-white">
                          {AGENT_MODES.find(m => m.id === selectedMode)?.label}
                        </span>
                        {showModeSelector ? (
                          <ChevronUpIcon className="w-4 h-4 text-gray-600 group-hover:text-gray-900 transition-colors dark:text-gray-400 dark:group-hover:text-white" />
                        ) : (
                          <ChevronDownIcon className="w-4 h-4 text-gray-600 group-hover:text-gray-900 transition-colors dark:text-gray-400 dark:group-hover:text-white" />
                        )}
                      </button>

                      {/* Text input - auto-growing textarea */}
                      <textarea
                        ref={inputRef}
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask Stanley anything about hockey analytics..."
                        rows={1}
                        className="flex-1 bg-transparent px-2 py-2 text-gray-900 placeholder-gray-500 text-sm font-military-chat focus:outline-none resize-none overflow-hidden dark:text-white dark:placeholder-gray-600"
                        style={{
                          minHeight: '24px',
                          maxHeight: '200px',
                          wordWrap: 'break-word',
                          whiteSpace: 'pre-wrap',
                          overflowWrap: 'break-word'
                        }}
                        disabled={isTyping}
                      />

                      {/* Right side buttons */}
                      <div className="flex items-center gap-1 flex-shrink-0">
                        {isTyping ? (
                          <button
                            onClick={() => {
                              setIsTyping(false)
                              setCurrentToolStatus(undefined)
                            }}
                            className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                            title="Stop generating"
                          >
                            <div className="w-3 h-3 bg-white rounded-sm" />
                          </button>
                        ) : (
                          inputValue.trim() ? (
                            <button
                              onClick={handleSendMessage}
                              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition-all duration-200 group"
                              title="Send message"
                            >
                              <PaperAirplaneIcon className="w-4 h-4 text-white group-hover:translate-x-0.5 transition-transform" />
                            </button>
                          ) : (
                            <div className="w-8 h-8 flex items-center justify-center">
                              <div className="w-3 h-3 rounded-full border border-gray-700" />
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Feature selection buttons - Grok-style */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.5, type: "spring", damping: 20 }}
                className="flex items-center justify-center gap-3 flex-wrap"
              >
                <button
                  onClick={() => {
                    setInputValue('Show me the latest game analysis')
                    inputRef.current?.focus()
                  }}
                  className="group flex items-center space-x-2 px-4 py-2.5 bg-black/20 backdrop-blur-sm border border-white/5 rounded-full hover:border-white/10 hover:bg-white/5 transition-all duration-200"
                >
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span className="text-sm font-military-display text-white">Latest Analysis</span>
                </button>

                <button
                  onClick={() => {
                    setInputValue('Compare top line combinations')
                    inputRef.current?.focus()
                  }}
                  className="group flex items-center space-x-2 px-4 py-2.5 bg-black/20 backdrop-blur-sm border border-white/5 rounded-full hover:border-white/10 hover:bg-white/5 transition-all duration-200"
                >
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span className="text-sm font-military-display text-white">Line Matchups</span>
                </button>

                <button
                  onClick={() => {
                    setInputValue('Show player performance trends')
                    inputRef.current?.focus()
                  }}
                  className="group flex items-center space-x-2 px-4 py-2.5 bg-black/20 backdrop-blur-sm border border-white/5 rounded-full hover:border-white/10 hover:bg-white/5 transition-all duration-200"
                >
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                  </svg>
                  <span className="text-sm font-military-display text-white">Player Stats</span>
                </button>

                <button
                  onClick={() => {
                    setInputValue('Predict next game lineup')
                    inputRef.current?.focus()
                  }}
                  className="group flex items-center space-x-2 px-4 py-2.5 bg-black/20 backdrop-blur-sm border border-white/5 rounded-full hover:border-white/10 hover:bg-white/5 transition-all duration-200"
                >
                  <svg className="w-4 h-4 text-gray-400 group-hover:text-white transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <span className="text-sm font-military-display text-white">Predictions</span>
                </button>
              </motion.div>

              {/* Status footer */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.7 }}
                className="flex items-center justify-center mt-8 text-[10px] text-gray-500"
              >
                <div className="flex items-center space-x-4">
                  <span className="font-military-display tracking-wider">SECURE CONNECTION</span>
                  <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                  <span className="font-military-display tracking-wider">STANLEY AI v2.1</span>
                  <div className="w-1 h-1 bg-gray-600 rounded-full"></div>
                  <span className="font-military-display tracking-wider">HEARTBEAT ENGINE</span>
                </div>
              </motion.div>
            </div>
            </motion.div>
          ) : (
            // CHAT INTERFACE - Traditional layout with messages
            <motion.div
              key="chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3 }}
              className="flex-1 flex flex-col"
            >
              {/* Chat messages area */}
              <div className="flex-1 overflow-y-auto px-4 pb-24">
                <div className="max-w-3xl mx-auto py-4">
                
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

              {/* Enhanced input area - Bottom fixed - ChatGPT Codex Style */}
              <div className="px-4 pb-6 border-t border-white/5">
                <div className="max-w-3xl mx-auto pt-3">
                  <div className="relative">
                    {/* Mode selector dropdown */}
                    <AnimatePresence>
                      {showModeSelector && (
                        <motion.div
                          ref={modeSelectorRef}
                          initial={{ opacity: 0, y: 10, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 10, scale: 0.95 }}
                          transition={{ duration: 0.15 }}
                          className="absolute bottom-full left-0 mb-2 w-48 bg-black/95 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl shadow-black/30 overflow-hidden"
                        >
                          <div className="p-1">
                            {AGENT_MODES.map((mode) => (
                              <button
                                key={mode.id}
                                onClick={() => {
                                  setSelectedMode(mode.id)
                                  setShowModeSelector(false)
                                }}
                                className={`w-full text-left px-3 py-2 rounded-md transition-all duration-150 ${
                                  selectedMode === mode.id
                                    ? 'bg-red-600/20'
                                    : 'hover:bg-white/5'
                                }`}
                              >
                                <div className="flex items-center justify-between mb-0.5">
                                  <span className="text-xs font-military-display text-white tracking-wider">
                                    {mode.label}
                                  </span>
                                  {selectedMode === mode.id && (
                                    <div className="w-1.5 h-1.5 bg-red-600 rounded-full"></div>
                                  )}
                                </div>
                                <p className="text-[10px] text-gray-500 leading-tight">
                                  {mode.description}
                                </p>
                              </button>
                            ))}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>

                    {/* Input container - Modern Codex style */}
                    <div className="relative rounded-2xl bg-black/20 backdrop-blur-md border border-white/5 shadow-2xl shadow-black/20 hover:border-white/10 transition-all duration-200">
                      <div className="flex items-center gap-2 px-3 py-2">
                        {/* Mode selector button */}
                        <button
                          onClick={() => setShowModeSelector(!showModeSelector)}
                          className="flex-shrink-0 flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-white/10 transition-colors group"
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

                        {/* Text input - auto-growing textarea */}
                        <textarea
                          ref={inputRef}
                          value={inputValue}
                          onChange={(e) => setInputValue(e.target.value)}
                          onKeyDown={handleKeyDown}
                          placeholder="Message STANLEY..."
                          rows={1}
                          className="flex-1 bg-transparent px-2 py-2 text-white placeholder-gray-600 text-sm font-military-chat focus:outline-none resize-none overflow-hidden"
                          style={{
                            minHeight: '24px',
                            maxHeight: '200px',
                            wordWrap: 'break-word',
                            whiteSpace: 'pre-wrap',
                            overflowWrap: 'break-word'
                          }}
                          disabled={isTyping}
                        />

                        {/* Right side buttons */}
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {isTyping ? (
                            <button
                              onClick={() => {
                                setIsTyping(false)
                                setCurrentToolStatus(undefined)
                              }}
                              className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                              title="Stop generating"
                            >
                              <div className="w-3 h-3 bg-white rounded-sm" />
                            </button>
                          ) : (
                            inputValue.trim() ? (
                              <button
                                onClick={handleSendMessage}
                                className="w-8 h-8 flex items-center justify-center rounded-lg bg-white/10 hover:bg-white/20 transition-all duration-200 group"
                                title="Send message"
                              >
                                <PaperAirplaneIcon className="w-4 h-4 text-white group-hover:translate-x-0.5 transition-transform" />
                              </button>
                            ) : (
                              <div className="w-8 h-8 flex items-center justify-center">
                                <div className="w-3 h-3 rounded-full border border-gray-700" />
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Character count indicator (optional) */}
                    {inputValue.length > 100 && (
                      <div className="absolute -top-5 right-2">
                        <span className="text-[9px] font-military-display text-gray-600 tabular-nums">
                          {inputValue.length}
                        </span>
                      </div>
                    )}
                  </div>
                
                  {/* Bottom hint text and status */}
                  <div className="mt-1.5 px-1 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-[8px] font-military-display text-gray-600 uppercase tracking-wider">
                      <span>SHIFT + ENTER</span>
                      <span className="text-gray-700">|</span>
                      <span>New Line</span>
                    </div>
                    
                      {currentToolStatus && (
                      <div className="flex items-center gap-1.5">
                        <div className="w-1 h-1 bg-red-500 rounded-full animate-pulse" />
                        <span className="text-[8px] font-military-display text-gray-500 uppercase tracking-wider">
                          {currentToolStatus === 'reasoning' && 'Processing...'}
                          {currentToolStatus === 'parquet_query' && 'Querying Data...'}
                          {currentToolStatus === 'synthesizing' && 'Generating...'}
                        </span>
                      </div>
                    )}
                  </div>

                  {/* Status footer */}
                  <div className="flex items-center justify-center mt-2 text-[10px] text-gray-600">
                    <div className="flex items-center space-x-3 font-military-display uppercase tracking-wider">
                      <span>Secure Connection</span>
                      <div className="w-0.5 h-0.5 bg-gray-700 rounded-full"></div>
                      <span>Stanley AI v2.1</span>
                      <div className="w-0.5 h-0.5 bg-gray-700 rounded-full"></div>
                      <span>HeartBeat Engine</span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
