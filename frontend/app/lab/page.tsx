'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { MilitarySidebar } from '../../components/military-sidebar/MilitarySidebar'
import { NeuralNetworkAnimation } from '../../components/layout/NeuralNetworkAnimation'
import { api } from '../../lib/api'

export default function LabPage() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
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
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-red-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <div className="text-white font-military-display text-sm">LOADING RESEARCH LAB...</div>
        </div>
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return (
    <main className="min-h-screen bg-black relative overflow-hidden">
      <MilitarySidebar 
        isOpen={sidebarOpen} 
        onToggle={() => setSidebarOpen(!sidebarOpen)}
        userInfo={userInfo}
        onLogout={handleLogout}
      />
      
      {/* Full screen immersive experience - no margin */}
      <div className="absolute inset-0">
        {/* Floating title */}
        <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-center px-6 py-6 pointer-events-none">
          <div className="text-center">
            <h1 className="text-xl font-bold text-white tracking-wider text-shadow-military font-military-display mb-2">
              GAME ANALYSIS
            </h1>
            <p className="text-sm text-gray-400 font-military-display">MTL vs TOR - Event Sequence Visualization</p>
          </div>
        </div>

        {/* Centered Neural Network Animation */}
        <div className="absolute inset-0 flex items-center justify-center" style={{ zIndex: 1 }}>
          <div className="w-full h-full">
            <NeuralNetworkAnimation className="w-full h-full" />
          </div>
        </div>
      </div>
    </main>
  )
}
