'use client'

import React, { useState, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { GlobalAISidebar } from './GlobalAISidebar'
import { AIToggleButton } from './AIToggleButton'

export function GlobalAIProvider({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const pathname = usePathname()

  // Determine current page for context
  const getCurrentPage = () => {
    if (!pathname) return 'page'
    if (pathname.includes('/analytics')) return 'analytics'
    if (pathname.includes('/schedule')) return 'schedule'
    if (pathname.includes('/scouting')) return 'scouting'
    if (pathname.includes('/video')) return 'video'
    if (pathname === '/') return 'dashboard'
    return 'page'
  }

  // Check if we should show AI toggle on this page
  const shouldShowAI = () => {
    if (!pathname) return false
    
    // Don't show on the main chat page (that's already STANLEY)
    if (pathname === '/chat') return false
    
    // Don't show on login/auth pages
    if (pathname.includes('/login') || pathname.includes('/auth')) return false
    
    return true
  }

  // Keyboard shortcut: Press 'S' to toggle
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only trigger if not typing in an input/textarea
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return
      }

      if (e.key === 's' || e.key === 'S') {
        if (shouldShowAI()) {
          setIsSidebarOpen(prev => !prev)
        }
      }

      // ESC to close
      if (e.key === 'Escape' && isSidebarOpen) {
        setIsSidebarOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => window.removeEventListener('keydown', handleKeyPress)
  }, [isSidebarOpen, pathname])

  // Close sidebar when navigating to chat page
  useEffect(() => {
    if (pathname === '/chat') {
      setIsSidebarOpen(false)
    }
  }, [pathname])

  return (
    <>
      {children}
      
      {shouldShowAI() && (
        <>
          <GlobalAISidebar
            isOpen={isSidebarOpen}
            onClose={() => setIsSidebarOpen(false)}
            currentPage={getCurrentPage()}
          />
          
          <AIToggleButton
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            isOpen={isSidebarOpen}
          />
        </>
      )}
    </>
  )
}

