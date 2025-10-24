'use client'

import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { LockClosedIcon, UserIcon, ShieldCheckIcon } from '@heroicons/react/24/outline'
import { EyeIcon, EyeSlashIcon } from '@heroicons/react/24/solid'
import { api } from '../../lib/api'

interface MilitaryAuthViewProps {
  onLogin: (userInfo: any) => void
}

export function MilitaryAuthView({ onLogin }: MilitaryAuthViewProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!username || !password) {
      setError('AUTHENTICATION REQUIRED')
      return
    }

    setIsLoading(true)
    
    try {
      // Call real API authentication
      const loginResponse = await api.login({ username, password })
      
      if (loginResponse.success && loginResponse.user_info && loginResponse.access_token) {
        // Store the token for API requests
        localStorage.setItem('heartbeat_token', loginResponse.access_token)
        onLogin(loginResponse.user_info)
      } else {
        setError('AUTHENTICATION FAILED')
      }
    } catch (error) {
      console.error('Login error:', error)
      setError('AUTHENTICATION FAILED')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col items-center justify-center px-4 relative overflow-hidden dark:bg-gray-950">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-30 dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(156, 163, 175, 0.15) 1px, transparent 1px),
            linear-gradient(90deg, rgba(156, 163, 175, 0.15) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>
      
      {/* Dark mode grid overlay */}
      <div className="absolute inset-0 opacity-0 dark:opacity-20">
        <div className="absolute inset-0" style={{
          backgroundImage: `
            linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
            linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
          `,
          backgroundSize: '50px 50px'
        }} />
      </div>

      {/* Radial gradient overlay */}
      <div className="absolute inset-0 bg-gradient-radial from-red-500/5 via-transparent to-transparent opacity-20 dark:from-red-600/5 dark:opacity-30" />

      {/* Pulse animation intentionally only on Analytics page */}
      
      {/* Top status bar */}
      <div className="absolute top-0 left-0 right-0 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-pulse" />
          <span className="text-xs text-gray-600 font-military-display uppercase tracking-wider dark:text-gray-400">Secure Access Point</span>
        </div>
        <span className="text-xs text-gray-600 font-military-display uppercase tracking-wider dark:text-gray-500">MTL-AUTH-V2.1</span>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Logo and Title */}
        <div className="text-center mb-12">
          <motion.h1 
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, type: "spring", damping: 20 }}
            className="text-4xl font-military-display text-gray-900 tracking-widest mb-3 dark:text-white"
          >
            HEARTBEAT
          </motion.h1>
          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xs text-gray-600 font-military-display uppercase tracking-widest dark:text-gray-500"
          >
            NHL Analytics Engine
          </motion.p>
        </div>

        {/* Auth Form */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4, type: "spring", damping: 20 }}
          className="bg-white/90 backdrop-blur-xl border border-gray-200 rounded-lg p-8 shadow-xl shadow-gray-300/50 dark:bg-black/40 dark:border-white/10 dark:shadow-white/5"
        >
          <div className="flex items-center justify-center space-x-2 mb-6">
            <div className="w-0.5 h-4 bg-gradient-to-b from-gray-900 to-transparent dark:from-white" />
            <h2 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
              Authentication Required
            </h2>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block text-xs font-military-display text-gray-600 uppercase tracking-wider mb-2 dark:text-gray-500">
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <UserIcon className="h-4 w-4 text-gray-500 dark:text-gray-600" />
                </div>
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="block w-full pl-10 pr-3 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 font-military-display text-sm focus:outline-none focus:ring-2 focus:ring-red-600/50 focus:border-red-600/50 transition-all hover:border-gray-400 dark:bg-black/40 dark:border-white/10 dark:text-white dark:placeholder-gray-600 dark:hover:border-white/20"
                  placeholder="Enter username"
                  disabled={isLoading}
                  autoComplete="username"
                />
              </div>
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-xs font-military-display text-gray-600 uppercase tracking-wider mb-2 dark:text-gray-500">
                Access Code
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <LockClosedIcon className="h-4 w-4 text-gray-500 dark:text-gray-600" />
                </div>
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="block w-full pl-10 pr-12 py-3 bg-white border border-gray-300 rounded-lg text-gray-900 placeholder-gray-500 font-military-display text-sm focus:outline-none focus:ring-2 focus:ring-red-600/50 focus:border-red-600/50 transition-all hover:border-gray-400 dark:bg-black/40 dark:border-white/10 dark:text-white dark:placeholder-gray-600 dark:hover:border-white/20"
                  placeholder="Enter access code"
                  disabled={isLoading}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  tabIndex={-1}
                >
                  {showPassword ? (
                    <EyeSlashIcon className="h-4 w-4 text-gray-500 hover:text-gray-700 transition-colors dark:text-gray-600 dark:hover:text-gray-400" />
                  ) : (
                    <EyeIcon className="h-4 w-4 text-gray-500 hover:text-gray-700 transition-colors dark:text-gray-600 dark:hover:text-gray-400" />
                  )}
                </button>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-red-600/10 border border-red-600/30 rounded-lg px-3 py-2"
              >
                <p className="text-xs text-red-600 font-military-chat text-center">
                  {error}
                </p>
              </motion.div>
            )}

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isLoading}
              className="w-full py-3 px-4 bg-red-600/10 hover:bg-red-600/20 disabled:bg-white/5 disabled:cursor-not-allowed text-red-400 hover:text-red-300 disabled:text-gray-600 font-military-display text-sm uppercase tracking-widest rounded-lg transition-all duration-200 border border-red-600/30 hover:border-red-600/50 disabled:border-white/10 focus:outline-none focus:ring-2 focus:ring-red-600/50"
            >
              {isLoading ? (
                <span className="flex items-center justify-center">
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  Authenticating...
                </span>
              ) : (
                'Initiate Access'
              )}
            </button>
          </form>

          {/* Security Notice */}
          <div className="mt-6 pt-6 border-t border-gray-200 dark:border-white/5">
            <p className="text-[10px] text-gray-600 text-center font-military-display uppercase tracking-wider dark:text-gray-500">
              Restricted Access • Authorized Personnel Only
            </p>
            <p className="text-[10px] text-gray-500 text-center font-military-display uppercase tracking-wider mt-1 dark:text-gray-600">
              All Access Attempts Are Monitored and Logged
            </p>
          </div>
        </motion.div>
      </motion.div>

      {/* Bottom status bar */}
      <div className="absolute bottom-0 left-0 right-0 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <ShieldCheckIcon className="w-3 h-3 text-gray-500 dark:text-gray-600" />
          <span className="text-xs text-gray-500 font-military-display uppercase tracking-wider dark:text-gray-600">Secure Connection</span>
        </div>
        <span className="text-xs text-gray-500 font-military-display uppercase tracking-wider dark:text-gray-600">HeartBeat Engine v2.1</span>
      </div>
    </div>
  )
}
