'use client'

import dynamic from 'next/dynamic'
import React from 'react'

// Dynamically import VegaLite to avoid SSR issues in Next.js
const VegaLite = dynamic(async () => {
  const mod = await import('react-vega')
  return mod.VegaLite
}, { ssr: false }) as any

interface VegaChartProps {
  spec: any
  width?: number
  height?: number
}

export function VegaChart({ spec, width = 480, height = 200 }: VegaChartProps) {
  // Ensure basic size
  const themeConfig = {
    background: 'transparent',
    config: {
      axis: {
        labelColor: '#9CA3AF',
        titleColor: '#9CA3AF',
        domainColor: '#374151',
        tickColor: '#374151'
      },
      view: { stroke: 'transparent' },
      range: {
        // enforce red-only palette for ordinal/nominal where used
        category: ['#EF4444'],
        ordinal: ['#EF4444']
      }
    }
  }
  const merged = {
    width,
    height,
    ...themeConfig,
    ...spec,
    config: {
      ...(themeConfig as any).config,
      ...(spec?.config || {})
    }
  }
  return (
    <div className="rounded border border-gray-800/50 overflow-hidden bg-gray-800/30">
      <VegaLite spec={merged} actions={false} renderer="svg" />
    </div>
  )
}
