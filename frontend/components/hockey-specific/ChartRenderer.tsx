'use client'

import React, { useMemo } from 'react'

type ChartKind = 'bar' | 'line'

interface ChartSpec {
  kind: ChartKind
  xKey: string
  yKey: string
  rows: Array<Record<string, any>>
}

interface ChartRendererProps {
  spec: ChartSpec
  width?: number
  height?: number
}

// Lightweight SVG chart renderer for Stanley chat
export function ChartRenderer({ spec, width = 480, height = 200 }: ChartRendererProps) {
  const padding = { top: 16, right: 16, bottom: 28, left: 40 }
  const innerW = Math.max(10, width - padding.left - padding.right)
  const innerH = Math.max(10, height - padding.top - padding.bottom)

  const { points, bars, xTicks, yTicks, yMax } = useMemo(() => {
    const rows = Array.isArray(spec?.rows) ? spec.rows : []
    const xKey = spec?.xKey
    const yKey = spec?.yKey
    const values = rows.map(r => Number(r?.[yKey] ?? 0))
    const maxV = values.length ? Math.max(...values) : 0
    const yMax = maxV === 0 ? 1 : maxV

    // Build categorical x scale (uniform spacing)
    const n = rows.length
    const step = n > 0 ? innerW / n : innerW

    const scaleY = (v: number) => innerH - (v / yMax) * innerH

    // Compute bar rects
    const bars = rows.map((r, i) => {
      const x = i * step
      const v = Number(r?.[yKey] ?? 0)
      const y = scaleY(v)
      const w = Math.max(2, step * 0.8)
      const h = innerH - y
      return { x, y, w, h, label: String(r?.[xKey]) || '' }
    })

    // Compute line points
    const points = rows.map((r, i) => {
      const v = Number(r?.[yKey] ?? 0)
      const x = i * step + step / 2
      const y = scaleY(v)
      return { x, y }
    })

    // Simple ticks: 0, 50%, 100%
    const yTicks = [0, yMax / 2, yMax].map(v => ({ v, y: scaleY(v) }))
    const xTicks = bars.map((b, i) => ({ x: i * step + step / 2, label: i % 2 === 0 ? bars[i].label : '' }))

    return { points, bars, xTicks, yTicks, yMax }
  }, [spec, innerW, innerH])

  // Build line path
  const pathD = useMemo(() => {
    if (!points?.length) return ''
    return points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
  }, [points])

  return (
    <svg width={width} height={height} className="block">
      {/* frame */}
      <rect x={0} y={0} width={width} height={height} fill="#0b0b0b" opacity={0} />
      {/* plotting area bg */}
      <g transform={`translate(${padding.left},${padding.top})`}>
        <rect x={0} y={0} width={innerW} height={innerH} fill="#111827" opacity={0.25} />
        {/* y gridlines */}
        {yTicks.map((t, idx) => (
          <g key={idx}>
            <line x1={0} y1={t.y} x2={innerW} y2={t.y} stroke="#374151" strokeWidth={0.5} opacity={0.4} />
            <text x={-8} y={t.y} textAnchor="end" dominantBaseline="middle" fill="#9CA3AF" fontSize={10}>
              {Math.round((t.v + Number.EPSILON) * 100) / 100}
            </text>
          </g>
        ))}

        {/* bars or line */}
        {spec.kind === 'bar' && (
          <g>
            {bars.map((b, i) => (
              <rect key={i} x={b.x + 1} y={b.y} width={Math.max(1, b.w - 2)} height={b.h} fill="#EF4444" opacity={0.8} rx={2} />
            ))}
          </g>
        )}
        {spec.kind === 'line' && pathD && (
          <>
            <path d={pathD} fill="none" stroke="#EF4444" strokeWidth={2} />
            {points.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={2} fill="#EF4444" />
            ))}
          </>
        )}

        {/* x labels (sparse) */}
        {xTicks.map((t, i) => (
          t.label ? (
            <text key={i} x={t.x} y={innerH + 14} textAnchor="middle" fill="#9CA3AF" fontSize={10}>
              {t.label}
            </text>
          ) : null
        ))}
      </g>
    </svg>
  )
}
