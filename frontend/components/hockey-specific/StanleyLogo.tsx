'use client'

import React from 'react'

interface StanleyLogoProps {
  className?: string
}

export function StanleyLogo({ className = "w-8 h-8" }: StanleyLogoProps) {
  return (
    <div className={`${className} relative`}>
      <svg
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="w-full h-full"
      >
        {/* Military-inspired logo design */}
        <rect
          x="2"
          y="2"
          width="28"
          height="28"
          rx="4"
          fill="currentColor"
          className="text-red-600"
        />
        
        {/* Central diamond pattern */}
        <path
          d="M16 6L22 12L16 18L10 12L16 6Z"
          fill="currentColor"
          className="text-white"
        />
        
        {/* Corner accents */}
        <rect x="4" y="4" width="2" height="2" fill="currentColor" className="text-military-white" />
        <rect x="26" y="4" width="2" height="2" fill="currentColor" className="text-military-white" />
        <rect x="4" y="26" width="2" height="2" fill="currentColor" className="text-military-white" />
        <rect x="26" y="26" width="2" height="2" fill="currentColor" className="text-military-white" />
        
        {/* Central 'S' for Stanley */}
        <path
          d="M14 20V22H18V20C18 19.4 17.6 19 17 19H15C14.4 19 14 19.4 14 20Z"
          fill="currentColor"
          className="text-red-600"
        />
        <path
          d="M14 14H18V16H14V14Z"
          fill="currentColor"
          className="text-red-600"
        />
        <path
          d="M14 10C14 9.4 14.4 9 15 9H17C17.6 9 18 9.4 18 10V12H14V10Z"
          fill="currentColor"
          className="text-red-600"
        />
      </svg>
    </div>
  )
}
