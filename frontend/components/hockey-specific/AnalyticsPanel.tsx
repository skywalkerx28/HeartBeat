'use client'

import React from 'react'
import { motion } from 'framer-motion'
import { 
  ChartBarIcon, 
  TableCellsIcon, 
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  VideoCameraIcon
} from '@heroicons/react/24/outline'
import { VideoClipsPanel } from './VideoClipsPanel'
import { EnhancedVideoClipsPanel } from './EnhancedVideoClipsPanel'
import { ChartRenderer } from './ChartRenderer'
import { VegaChart } from './VegaChart'

interface ClipData {
  clip_id: string
  title: string
  player_name: string
  game_info: string
  event_type: string
  description: string
  file_url: string
  thumbnail_url: string
  duration: number
  relevance_score?: number
}

interface AnalyticsData {
  type: 'stat' | 'chart' | 'table' | 'clips'
  title: string
  data: any
  clips?: ClipData[]
}

interface AnalyticsPanelProps {
  analytics: AnalyticsData[]
}

export function AnalyticsPanel({ analytics }: AnalyticsPanelProps) {
  return (
    <div className="space-y-4">
      {analytics.map((item, index) => (
        <motion.div
          key={`${item.type}-${index}`}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.1, duration: 0.3 }}
          className="bg-gray-900/50 border border-gray-800 rounded-lg p-4 backdrop-blur-sm"
        >
          {/* Panel header */}
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              {item.type === 'stat' && <ChartBarIcon className="w-4 h-4 text-gray-400" />}
              {item.type === 'chart' && <ArrowTrendingUpIcon className="w-4 h-4 text-white" />}
              {item.type === 'table' && <TableCellsIcon className="w-4 h-4 text-gray-400" />}
              {item.type === 'clips' && <VideoCameraIcon className="w-4 h-4 text-red-500" />}
              <h3 className="text-sm font-medium text-white">
                {item.title}
              </h3>
            </div>
            <span className="text-xs font-mono text-gray-400">
              {item.type === 'clips' ? 'VIDEO DATA' : 'LIVE DATA'}
            </span>
          </div>

          {/* Panel content based on type */}
          {item.type === 'stat' && (
            <StatCard data={item.data} />
          )}
          
          {item.type === 'chart' && item.data && (item.data.vegaLite) && (
            <VegaChart spec={(item.data as any).vegaLite} />
          )}
          {item.type === 'chart' && item.data && item.data.kind && !item.data.vegaLite && (
            <ChartRenderer spec={item.data as any} />
          )}
          {item.type === 'chart' && (!item.data || !item.data.kind) && (
            <ChartPreview data={item.data} />
          )}
          
          {item.type === 'table' && (
            <TablePreview data={item.data} />
          )}
          
          {item.type === 'clips' && (
            <EnhancedVideoClipsPanel clips={item.clips || []} title={item.title} />
          )}
        </motion.div>
      ))}
    </div>
  )
}

function StatCard({ data }: { data: any }) {
  // Filter out complex nested objects/arrays and only show simple values
  const simpleStats = Object.entries(data).filter(([key, value]) => {
    // Only include primitive values (strings, numbers, booleans)
    return typeof value !== 'object' || value === null
  })
  
  // If no simple stats, show key metrics
  if (simpleStats.length === 0) {
    return (
      <div className="space-y-2">
        <div className="text-sm text-gray-400">
          {data.analysis_type && (
            <div className="mb-1">
              <span className="text-white font-medium">Analysis:</span> {data.analysis_type}
            </div>
          )}
          {data.season && (
            <div className="mb-1">
              <span className="text-white font-medium">Season:</span> {data.season}
            </div>
          )}
          {data.total_pp_units !== undefined && (
            <div className="mb-1">
              <span className="text-white font-medium">PP Units:</span> {data.total_pp_units}
            </div>
          )}
          {data.opponent && (
            <div className="mb-1">
              <span className="text-white font-medium">Opponent:</span> {data.opponent}
            </div>
          )}
        </div>
      </div>
    )
  }
  
  return (
    <div className="grid grid-cols-3 gap-4">
      {simpleStats.slice(0, 6).map(([key, value]) => (
        <div key={key} className="text-center">
          <div className="text-lg font-bold text-white font-mono">
            {String(value)}
          </div>
          <div className="text-xs text-gray-400 uppercase tracking-wide">
            {key.replace(/_/g, ' ')}
          </div>
        </div>
      ))}
    </div>
  )
}

function ChartPreview({ data }: { data: any }) {
  return (
    <div className="h-24 bg-gray-800/30 rounded border border-gray-800/50 flex items-center justify-center">
      <div className="text-center">
        <ArrowTrendingUpIcon className="w-8 h-8 text-white mx-auto mb-1" />
        <div className="text-xs text-gray-400">
          Chart visualization will render here
        </div>
      </div>
    </div>
  )
}

function TablePreview({ data }: { data: any }) {
  // Expect shape: { columns: [{key, label}], rows: [{...}] }
  const columns: Array<{ key: string; label?: string }> = Array.isArray(data?.columns) ? data.columns : []
  const rows: Array<Record<string, any>> = Array.isArray(data?.rows) ? data.rows : []

  // Detect schedule tables (Home/Away with Start time)
  const colKeys = new Set(columns.map(c => c.key))
  const isSchedule = colKeys.has('home') && colKeys.has('away') && (colKeys.has('start_time_utc') || colKeys.has('start'))

  if (columns.length === 0 || rows.length === 0) {
    // Fallback placeholder when no structured data provided
    return (
      <div className="text-xs text-gray-400 font-military-chat">
        No tabular data available.
      </div>
    )
  }

  // Special layout for schedule: tighter Home/Away columns and no STATE if present
  if (isSchedule) {
    const schedCols = columns.filter(c => c.key !== 'game_state' && c.key !== 'state')
    const showResult = colKeys.has('result')
    const tpl = showResult ? '110px 64px 64px 72px 1fr' : '110px 64px 64px 1fr' // Date | Home | Away | [Result] | Start
    const labelByKey = Object.fromEntries(schedCols.map(c => [c.key, c.label || c.key]))
    return (
      <div className="space-y-2">
        {/* Header */}
        <div className="grid gap-2 pb-2 border-b border-gray-800/50" style={{ gridTemplateColumns: tpl }}>
          <div className="text-xs font-medium text-gray-400 uppercase truncate">{labelByKey['date'] || 'Date'}</div>
          <div className="text-xs font-medium text-gray-400 uppercase truncate">{labelByKey['home'] || 'Home'}</div>
          <div className="text-xs font-medium text-gray-400 uppercase truncate">{labelByKey['away'] || 'Away'}</div>
          {showResult && <div className="text-xs font-medium text-gray-400 uppercase truncate">{labelByKey['result'] || 'Result'}</div>}
          <div className="text-xs font-medium text-gray-400 uppercase truncate">{labelByKey['start_time_utc'] || labelByKey['start'] || 'Start'}</div>
        </div>
        {/* Rows (all games, scrollable) */}
        <div className="max-h-96 overflow-y-auto pr-1">
          {rows.map((r, i) => (
            <div key={i} className="grid gap-2 py-1" style={{ gridTemplateColumns: tpl }}>
              {/* Date */}
              <div className="text-xs text-white font-mono truncate">{formatCell(r['date'])}</div>
              {/* Home */}
              <div className="text-xs text-white font-mono text-center">{formatCell(r['home'])}</div>
              {/* Away */}
              <div className="text-xs text-white font-mono text-center">{formatCell(r['away'])}</div>
              {/* Result (optional) */}
              {showResult && (
                <div className="text-xs text-white font-mono text-center">{formatCell(r['result'])}</div>
              )}
              {/* Start */}
              <div className="text-xs text-white font-mono truncate">{formatCell(r['start_time_utc'] ?? r['start'])}</div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  const colCount = Math.min(columns.length, 6)

  return (
    <div className="space-y-2">
      {/* Header */}
      <div className={`grid gap-2 pb-2 border-b border-gray-800/50`} style={{ gridTemplateColumns: `repeat(${colCount}, minmax(0, 1fr))` }}>
        {columns.slice(0, colCount).map((c) => (
          <div key={c.key} className="text-xs font-medium text-gray-400 uppercase truncate">
            {c.label || c.key}
          </div>
        ))}
      </div>
      {/* Rows (all, scrollable) */}
      <div className="max-h-96 overflow-y-auto pr-1">
        {rows.map((r, i) => (
          <div key={i} className={`grid gap-2 py-1`} style={{ gridTemplateColumns: `repeat(${colCount}, minmax(0, 1fr))` }}>
            {columns.slice(0, colCount).map((c) => (
              <div key={c.key} className="text-xs text-white font-mono truncate">
                {formatCell(r[c.key])}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

function formatCell(val: any): string {
  if (val === null || val === undefined) return ''
  if (typeof val === 'number') return String(Math.round((val + Number.EPSILON) * 100) / 100)
  return String(val)
}

function ClipsPreview({ clips, title }: { clips: ClipData[], title: string }) {
  // For preview in analytics panel, show a simplified version
  if (clips.length === 0) {
    return (
      <div className="text-center py-4">
        <VideoCameraIcon className="w-8 h-8 text-gray-600 mx-auto mb-2" />
        <p className="text-xs text-gray-400">
          No video clips available
        </p>
      </div>
    )
  }

  // Show compact preview for first few clips
  const previewClips = clips.slice(0, 3)
  
  return (
    <div className="space-y-2">
      {previewClips.map((clip, index) => (
        <div key={`${clip.clip_id}-${index}`} className="flex items-center space-x-3 p-2 bg-gray-800/30 rounded border border-gray-700/50">
          <div className="flex-shrink-0 w-12 h-8 bg-black rounded overflow-hidden">
            <img 
              src={clip.thumbnail_url} 
              alt={clip.title}
              className="w-full h-full object-cover"
            />
          </div>
          <div className="flex-1 min-w-0">
            <h4 className="text-xs font-medium text-white truncate">
              {clip.title}
            </h4>
            <p className="text-xs text-gray-400 truncate">
              {clip.player_name} • {Math.round(clip.duration)}s
            </p>
          </div>
        </div>
      ))}
      
      {clips.length > 3 && (
        <div className="text-center pt-2 border-t border-gray-800/50">
          <span className="text-xs text-gray-400 font-mono">
            +{clips.length - 3} more clips
          </span>
        </div>
      )}
    </div>
  )
}
