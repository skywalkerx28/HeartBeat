'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { MilitaryAuthView } from '../components/auth/MilitaryAuthView'
import { api } from '../lib/api'

export default function HomePage() {
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  // Check for existing authentication on component mount
  useEffect(() => {
    const storedUser = localStorage.getItem('heartbeat_user')
    const storedToken = localStorage.getItem('heartbeat_token')
    
    if (storedUser && storedToken) {
      // User is already authenticated, redirect to analytics dashboard
      router.push('/analytics')
    } else {
      // No authentication, show login page
      setLoading(false)
    }
  }, [router])

  const handleLogin = (userInfo: any) => {
    // Store user info from successful API authentication
    localStorage.setItem('heartbeat_user', JSON.stringify(userInfo))
    
    // Redirect to analytics dashboard after successful login
    router.push('/analytics')
  }

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center dark:bg-gray-950">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-gray-900 font-military-display text-sm dark:text-white">INITIALIZING HEARTBEAT...</div>
        </div>
      </div>
    )
  }

  // Show auth view
  return <MilitaryAuthView onLogin={handleLogin} />
}
