'use client'

import Link from 'next/link'
import { ReactNode } from 'react'

interface TeamLinkProps {
  teamId: string
  children: ReactNode
  className?: string
  showHover?: boolean
}

export function TeamLink({ teamId, children, className = '', showHover = true }: TeamLinkProps) {
  const baseClasses = showHover 
    ? 'transition-colors hover:text-red-600 hover:underline cursor-pointer'
    : ''
  
  return (
    <Link 
      href={`/team/${teamId}`}
      className={`${baseClasses} ${className}`}
    >
      {children}
    </Link>
  )
}

