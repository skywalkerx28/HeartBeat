'use client'

import Link from 'next/link'
import { ReactNode } from 'react'

interface PlayerLinkProps {
  playerId: string | number
  children: ReactNode
  className?: string
  showHover?: boolean
}

export function PlayerLink({ playerId, children, className = '', showHover = true }: PlayerLinkProps) {
  const baseClasses = showHover 
    ? 'transition-colors hover:text-red-600 hover:underline cursor-pointer'
    : ''
  
  return (
    <Link 
      href={`/player/${playerId}`}
      className={`${baseClasses} ${className}`}
    >
      {children}
    </Link>
  )
}

