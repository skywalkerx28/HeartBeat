'use client'

import { useState, useEffect } from 'react'
import { ChartBarIcon, CpuChipIcon, WifiIcon } from '@heroicons/react/24/outline'

interface Metric {
  id: string
  label: string
  value: string | number
  unit: string
  trend: 'up' | 'down' | 'stable'
  color: string
  timestamp: number
}

interface PerformanceMetrics {
  totalPredictions: number
  avgLatencyMs: number
  p95LatencyMs: number
  maxLatencyMs: number
  avgConfidence: number
  recentPredictions: number
  systemUptime: number
  modelAccuracy: number
  predictionsPerSecond: number
  memoryUsage: number
  cacheSize: number
  temperature: number
}

interface PulseMetricsStreamProps {
  performanceMetrics?: PerformanceMetrics
}

export function PulseMetricsStream({ performanceMetrics }: PulseMetricsStreamProps) {
  const [metrics, setMetrics] = useState<Metric[]>(() => {
    // Use real backend metrics if available, otherwise fall back to mock data
    if (performanceMetrics) {
      return [
        {
          id: 'latency',
          label: 'INFERENCE LATENCY',
          value: performanceMetrics.avgLatencyMs,
          unit: 'ms',
          trend: 'stable',
          color: 'text-gray-300',
          timestamp: Date.now()
        },
        {
          id: 'accuracy',
          label: 'MODEL ACCURACY',
          value: performanceMetrics.modelAccuracy,
          unit: '%',
          trend: 'up',
          color: 'text-red-400',
          timestamp: Date.now()
        },
        {
          id: 'confidence',
          label: 'AVG CONFIDENCE',
          value: performanceMetrics.avgConfidence,
          unit: '',
          trend: 'stable',
          color: 'text-gray-400',
          timestamp: Date.now()
        },
        {
          id: 'predictions',
          label: 'PREDICTIONS/SEC',
          value: performanceMetrics.predictionsPerSecond,
          unit: '',
          trend: 'up',
          color: 'text-gray-300',
          timestamp: Date.now()
        },
        {
          id: 'memory',
          label: 'MEMORY USAGE',
          value: performanceMetrics.memoryUsage,
          unit: 'GB',
          trend: 'stable',
          color: 'text-gray-400',
          timestamp: Date.now()
        },
        {
          id: 'uptime',
          label: 'SYSTEM UPTIME',
          value: performanceMetrics.systemUptime,
          unit: '%',
          trend: 'stable',
          color: 'text-red-400',
          timestamp: Date.now()
        },
        {
          id: 'total_predictions',
          label: 'TOTAL PREDICTIONS',
          value: performanceMetrics.totalPredictions,
          unit: '',
          trend: 'up',
          color: 'text-blue-400',
          timestamp: Date.now()
        },
        {
          id: 'cache_size',
          label: 'CACHE SIZE',
          value: performanceMetrics.cacheSize,
          unit: '',
          trend: 'stable',
          color: 'text-green-400',
          timestamp: Date.now()
        },
        {
          id: 'p95_latency',
          label: 'P95 LATENCY',
          value: performanceMetrics.p95LatencyMs,
          unit: 'ms',
          trend: 'stable',
          color: 'text-orange-400',
          timestamp: Date.now()
        }
      ]
    }

    // Fallback mock data
    return [
      {
        id: 'latency',
        label: 'INFERENCE LATENCY',
        value: 8.7,
        unit: 'ms',
        trend: 'stable',
        color: 'text-gray-300',
        timestamp: Date.now()
      },
      {
        id: 'accuracy',
        label: 'MODEL ACCURACY',
        value: 87.3,
        unit: '%',
        trend: 'up',
        color: 'text-red-400',
        timestamp: Date.now()
      },
      {
        id: 'confidence',
        label: 'AVG CONFIDENCE',
        value: 0.82,
        unit: '',
        trend: 'stable',
        color: 'text-gray-400',
        timestamp: Date.now()
      },
      {
        id: 'predictions',
        label: 'PREDICTIONS/SEC',
        value: 12.4,
        unit: '',
        trend: 'up',
        color: 'text-gray-300',
        timestamp: Date.now()
      },
      {
        id: 'memory',
        label: 'MEMORY USAGE',
        value: 2.1,
        unit: 'GB',
        trend: 'stable',
        color: 'text-gray-400',
        timestamp: Date.now()
      },
      {
        id: 'uptime',
        label: 'SYSTEM UPTIME',
        value: 99.7,
        unit: '%',
        trend: 'stable',
        color: 'text-red-400',
        timestamp: Date.now()
      }
    ]
  })

  const [streamLines, setStreamLines] = useState<string[]>([])

  // Simulate real-time metric updates
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => prev.map(metric => ({
        ...metric,
        value: typeof metric.value === 'number'
          ? metric.value + (Math.random() - 0.5) * 0.1 // Small random fluctuation
          : metric.value,
        timestamp: Date.now()
      })))
    }, 2000)

    return () => clearInterval(interval)
  }, [])

  // Generate matrix-style data stream
  useEffect(() => {
    const streamInterval = setInterval(() => {
      const chars = '0123456789ABCDEF'
      const line = Array.from({ length: 40 }, () =>
        chars[Math.floor(Math.random() * chars.length)]
      ).join('')

      setStreamLines(prev => {
        const newLines = [line, ...prev.slice(0, 9)] // Keep last 10 lines
        return newLines
      })
    }, 100)

    return () => clearInterval(streamInterval)
  }, [])

  const getTrendIcon = (trend: string) => {
    switch (trend) {
      case 'up': return '↗'
      case 'down': return '↘'
      default: return '→'
    }
  }

  const formatValue = (value: string | number, unit: string) => {
    if (typeof value === 'number') {
      if (unit === '%') return `${value.toFixed(1)}${unit}`
      if (unit === 'ms') return `${value.toFixed(1)}${unit}`
      if (unit === 'GB') return `${value.toFixed(1)}${unit}`
      return value.toFixed(2)
    }
    return `${value}${unit}`
  }

  return (
    <div
      className="bg-gray-900/80 border border-gray-700 rounded-lg p-4 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center space-x-3 mb-4">
        <ChartBarIcon className="w-5 h-5 text-gray-400" />
        <div>
          <h3 className="text-lg font-military-display text-white">
            METRICS STREAM
          </h3>
          <p className="text-xs font-military-display text-gray-400">
            REAL-TIME PERFORMANCE
          </p>
        </div>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3 mb-4">
        {metrics.map((metric) => (
          <div
            key={metric.id}
            className="bg-gray-800/50 border border-gray-700 rounded-lg p-3 text-center"
          >
            <div className="text-xs font-military-display text-gray-500 mb-1 tracking-wider">
              {metric.label}
            </div>
            <div className={`text-lg font-military-display font-bold ${metric.color} mb-1`}>
              {formatValue(metric.value, metric.unit)}
            </div>
            <div className="text-xs font-military-display text-gray-400">
              {getTrendIcon(metric.trend)}
            </div>
          </div>
        ))}
      </div>

      {/* Data Stream Visualization */}
      <div className="relative">
        <div className="text-xs font-military-display text-gray-500 mb-2 tracking-wider">
          NEURAL DATA STREAM
        </div>

        <div className="bg-black/50 border border-gray-700 rounded-lg p-3 h-24 overflow-hidden relative">
          {/* Static data display */}
          <div className="font-mono text-xs text-gray-400 leading-tight">
            {streamLines.slice(0, 3).map((line, index) => (
              <div key={`${line}-${index}`} className="whitespace-nowrap">
                {line}
              </div>
            ))}
          </div>

          {/* Static connection indicators */}
          <div className="absolute bottom-2 left-2 flex items-center space-x-2">
            <div className="w-1.5 h-1.5 bg-red-500 rounded-full"></div>
            <WifiIcon className="w-3 h-3 text-red-400" />
          </div>

          <div className="absolute bottom-2 right-2">
            <div className="w-3 h-3 border border-gray-400 border-t-transparent rounded-full"></div>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="mt-3 flex items-center justify-center space-x-4 text-xs font-military-display">
        <div className="flex items-center space-x-1">
          <div className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse"></div>
          <span className="text-red-400">CONNECTED</span>
        </div>
        <div className="w-px h-3 bg-gray-600"></div>
        <div className="flex items-center space-x-1">
          <CpuChipIcon className="w-3 h-3 text-gray-400" />
          <span className="text-gray-400">PROCESSING</span>
        </div>
        <div className="w-px h-3 bg-gray-600"></div>
        <div className="flex items-center space-x-1">
          <div className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-pulse"></div>
          <span className="text-gray-400">SYNCED</span>
        </div>
      </div>

    </div>
  )
}
