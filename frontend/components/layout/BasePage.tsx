'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import clsx from 'clsx'
import { MilitarySidebar } from '../military-sidebar/MilitarySidebar'
import { api } from '../../lib/api'

interface BasePageProps {
  children: React.ReactNode
  loadingMessage?: string
}

export function BasePage({ children, loadingMessage = 'LOADING...' }: BasePageProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [userInfo, setUserInfo] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const router = useRouter()

  useEffect(() => {
    const storedUser = localStorage.getItem('heartbeat_user')
    const storedToken = localStorage.getItem('heartbeat_token')
    
    if (storedUser && storedToken) {
      try {
        const userData = JSON.parse(storedUser)
        setUserInfo(userData)
        setIsAuthenticated(true)
        api.setAccessToken(storedToken)
      } catch (error) {
        console.error('Error parsing stored user data:', error)
        localStorage.removeItem('heartbeat_user')
        localStorage.removeItem('heartbeat_token')
        router.push('/')
      }
    } else {
      router.push('/')
    }
    
    setLoading(false)
  }, [router])

  const handleLogout = () => {
    setIsAuthenticated(false)
    setUserInfo(null)
    setSidebarOpen(false)
    localStorage.removeItem('heartbeat_user')
    localStorage.removeItem('heartbeat_token')
    api.clearAccessToken()
    router.push('/')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center dark:bg-gray-950">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-gray-700 font-military-display text-sm dark:text-white">{loadingMessage}</div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <main className="min-h-screen bg-gray-50 relative dark:bg-gray-950">
      <MilitarySidebar 
        isOpen={sidebarOpen} 
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        userInfo={userInfo}
        onLogout={handleLogout}
      />
      <div className={clsx(
        'transition-all duration-300',
        sidebarOpen ? 'ml-80' : 'ml-16'
      )}>
        {children}
      </div>
    </main>
  )
}
