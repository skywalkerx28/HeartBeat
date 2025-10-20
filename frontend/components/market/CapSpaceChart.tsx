'use client'

import React from 'react'
import { motion } from 'framer-motion'

interface CapProjection {
  season: string
  capSpace: number
  committed: number
  projected: number
  capFloor?: number
}

interface CapSpaceChartProps {
  projections: CapProjection[]
  currentCapSpace: number
  accruedCapSpace: number
  deadlineCapSpace: number
}

export function CapSpaceChart({ 
  projections, 
  currentCapSpace, 
  accruedCapSpace,
  deadlineCapSpace 
}: CapSpaceChartProps) {
  
  // Dynamic Y-axis scaling for better readability
  // Use min committed value as baseline, max ceiling as top
  const minCommitted = Math.min(...projections.map(p => p.committed))
  const maxCeiling = Math.max(...projections.map(p => p.projected))
  
  // Add 10% padding at top and bottom for visual breathing room
  const padding = (maxCeiling - minCommitted) * 0.1
  const yMin = Math.max(0, minCommitted - padding)
  const yMax = maxCeiling + padding
  const yRange = yMax - yMin
  
  // Generate data points for the area chart with dynamic range
  const getYPosition = (value: number, height: number) => {
    const normalized = (value - yMin) / yRange
    return height - (normalized * height)
  }

  const chartHeight = 280
  const chartWidth = 100 // percentage

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.1 }}
      className="relative w-full"
    >
      {/* Floating Chart Container - No modal background */}
      <div className="relative h-80 w-full">
        
        {/* Chart Title (Floating Above) */}
        <div className="flex items-center justify-between mb-4 px-2">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
              Cap Space Trajectory
            </h3>
          </div>
          <div className="flex items-center space-x-4 text-[10px] font-military-display text-gray-500">
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 bg-white/30 rounded-sm" />
              <span>Cap Ceiling</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 bg-red-600/40 rounded-sm" />
              <span>Committed</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 bg-white/60 rounded-sm" />
              <span>Available</span>
            </div>
          </div>
        </div>

        {/* SVG Chart Area */}
        <div className="relative h-72 w-full border border-white/5 rounded-lg overflow-hidden">
          {/* Grid Lines (Horizontal) */}
          <div className="absolute inset-0">
            {[0, 20, 40, 60, 80, 100].map((pct) => (
              <div
                key={pct}
                className="absolute left-0 right-0 border-t border-white/5"
                style={{ top: `${pct}%` }}
              >
                <span className="absolute -left-2 -top-2 text-[9px] font-military-display text-gray-600 tabular-nums">
                  ${((yMax - (yRange * pct / 100)) / 1000000).toFixed(0)}M
                </span>
              </div>
            ))}
          </div>

          {/* Vertical Grid Lines (Seasons) */}
          <div className="absolute inset-0">
            {projections.map((proj, idx) => (
              <div
                key={proj.season}
                className="absolute top-0 bottom-0 border-l border-white/5"
                style={{ left: `${(idx / (projections.length - 1)) * 100}%` }}
              />
            ))}
          </div>

          {/* SVG for Lines and Areas */}
          <svg className="absolute inset-0 w-full h-full" preserveAspectRatio="none">
            <defs>
              {/* Gradient for cap ceiling area */}
              <linearGradient id="capCeilingGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(255, 255, 255, 0.1)" />
                <stop offset="100%" stopColor="rgba(255, 255, 255, 0.02)" />
              </linearGradient>
              
              {/* Gradient for committed area */}
              <linearGradient id="committedGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(239, 68, 68, 0.3)" />
                <stop offset="100%" stopColor="rgba(239, 68, 68, 0.05)" />
              </linearGradient>

              {/* Gradient for available space area */}
              <linearGradient id="availableGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="rgba(255, 255, 255, 0.2)" />
                <stop offset="100%" stopColor="rgba(255, 255, 255, 0.03)" />
              </linearGradient>
            </defs>

            {/* Cap Ceiling Line (top boundary) */}
            <motion.polyline
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 1.5, delay: 0.2 }}
              fill="none"
              stroke="rgba(255, 255, 255, 0.3)"
              strokeWidth="1.5"
              points={projections.map((proj, idx) => {
                const x = (idx / (projections.length - 1)) * 100
                const y = getYPosition(proj.projected, 100)
                return `${x},${y}`
              }).join(' ')}
              vectorEffect="non-scaling-stroke"
            />

            {/* Committed Cap Area (filled) */}
            <motion.polygon
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 1, delay: 0.4 }}
              fill="url(#committedGradient)"
              points={
                projections.map((proj, idx) => {
                  const x = (idx / (projections.length - 1)) * 100
                  const y = getYPosition(proj.committed, 100)
                  return `${x},${y}`
                }).join(' ') +
                ` 100,100 0,100`
              }
            />

            {/* Committed Cap Line */}
            <motion.polyline
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: 1 }}
              transition={{ duration: 1.5, delay: 0.6 }}
              fill="none"
              stroke="rgba(239, 68, 68, 0.8)"
              strokeWidth="2"
              points={projections.map((proj, idx) => {
                const x = (idx / (projections.length - 1)) * 100
                const y = getYPosition(proj.committed, 100)
                return `${x},${y}`
              }).join(' ')}
              vectorEffect="non-scaling-stroke"
            />

            {/* Data Points on Lines */}
            {projections.map((proj, idx) => {
              const x = (idx / (projections.length - 1)) * 100
              const yCommitted = getYPosition(proj.committed, 100)
              const yProjected = getYPosition(proj.projected, 100)
              
              return (
                <g key={proj.season}>
                  {/* Committed point */}
                  <motion.circle
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.8 + idx * 0.1, duration: 0.3 }}
                    cx={`${x}%`}
                    cy={`${yCommitted}%`}
                    r="3"
                    fill="rgba(239, 68, 68, 0.9)"
                    stroke="rgba(239, 68, 68, 1)"
                    strokeWidth="1"
                  />
                  {/* Ceiling point */}
                  <motion.circle
                    initial={{ scale: 0, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    transition={{ delay: 0.8 + idx * 0.1, duration: 0.3 }}
                    cx={`${x}%`}
                    cy={`${yProjected}%`}
                    r="2.5"
                    fill="rgba(255, 255, 255, 0.4)"
                    stroke="rgba(255, 255, 255, 0.6)"
                    strokeWidth="1"
                  />
                </g>
              )
            })}
          </svg>

          {/* Season Labels (Bottom) */}
          <div className="absolute bottom-0 left-0 right-0 flex justify-between px-2 pb-2">
            {projections.map((proj, idx) => (
              <div key={proj.season} className="flex-1 text-center">
                <div className="text-[10px] font-military-display text-gray-500">
                  {proj.season}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Floating Stats Overlay (Bottom Right) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.2 }}
          className="absolute bottom-8 right-4 bg-black/60 backdrop-blur-xl border border-white/20 rounded-lg p-4 min-w-[280px]"
        >
          <div className="space-y-2 text-xs font-military-display">
            <div className="flex justify-between items-center pb-2 border-b border-white/10">
              <span className="text-gray-500 uppercase tracking-wider text-[9px]">Current Space</span>
              <span className="text-white tabular-nums text-sm">
                ${(currentCapSpace / 1000000).toFixed(2)}M
              </span>
            </div>
            <div className="flex justify-between items-center pb-2 border-b border-white/10">
              <span className="text-gray-500 uppercase tracking-wider text-[9px]">Accrued YTD</span>
              <span className="text-white tabular-nums">
                ${(accruedCapSpace / 1000000).toFixed(2)}M
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-500 uppercase tracking-wider text-[9px]">Deadline Power</span>
              <span className="text-red-400 tabular-nums">
                ${(deadlineCapSpace / 1000000).toFixed(2)}M
              </span>
            </div>
          </div>
        </motion.div>
      </div>
    </motion.div>
  )
}

