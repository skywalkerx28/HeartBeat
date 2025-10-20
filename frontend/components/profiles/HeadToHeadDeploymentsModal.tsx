'use client'

import React, { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { getTeamAdvancedMetrics, getGameDeployments, resolvePlayerNames, TeamAdvancedMetrics, PlayerNameEntry } from '../../lib/profileApi'

interface Props {
  teamId: string
  opponent: string
  onClose: () => void
}

function mmss(totalSec?: number | null): string {
  if (totalSec == null || Number.isNaN(totalSec)) return '--:--'
  const s = Math.max(0, Math.round(totalSec))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

export function HeadToHeadDeploymentsModal({ teamId, opponent, onClose }: Props) {
  const [loading, setLoading] = useState(true)
  const [adv, setAdv] = useState<TeamAdvancedMetrics | null>(null)
  const [gameId, setGameId] = useState<number | null>(null)
  const [gameMeta, setGameMeta] = useState<{ home?: string; away?: string } | null>(null)
  const [deployments, setDeployments] = useState<any[]>([])
  const [periodOpeners, setPeriodOpeners] = useState<any[]>([])
  const [periodSel, setPeriodSel] = useState<string>('ALL')
  const [strengthSel, setStrengthSel] = useState<string>('ALL')
  const [names, setNames] = useState<Record<string, PlayerNameEntry>>({})

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      try {
        const advData = await getTeamAdvancedMetrics(teamId)
        if (!advData) return
        if (cancelled) return
        setAdv(advData)

        // Latest game vs opponent
        const games = (advData.games || []).filter((g: any) => String(g.opponent || '') === opponent)
        const latest = games
          .map((g: any) => ({ g, ts: g.gameDate ? Date.parse(g.gameDate) : 0 }))
          .sort((a, b) => b.ts - a.ts)[0]
        const gid = latest?.g?.gameId
        if (!gid) return
        setGameId(Number(gid))

        const gd = await getGameDeployments(gid)
        if (cancelled) return
        setGameMeta({ home: gd.home_team_code, away: gd.away_team_code })
        setDeployments(gd.deployments || [])
        setPeriodOpeners(gd.period_openers || [])

        // Resolve names
        const ids = new Set<string>()
        const gather = (arr?: any[]) => {
          for (const d of arr || []) {
            ;(d.home_forwards || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.home_defense || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.away_forwards || []).forEach((x: any) => x && ids.add(String(x)))
            ;(d.away_defense || []).forEach((x: any) => x && ids.add(String(x)))
          }
        }
        gather(gd.deployments)
        gather(gd.period_openers)
        if (ids.size) {
          const map = await resolvePlayerNames(Array.from(ids))
          if (!cancelled) setNames(map || {})
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => { cancelled = true }
  }, [teamId, opponent])

  const strengths = useMemo(() => {
    const s = new Set<string>()
    deployments.forEach(d => { if (d.strength) s.add(String(d.strength)) })
    return ['ALL', ...Array.from(s)]
  }, [deployments])

  const periods = useMemo(() => {
    const p = new Set<number>()
    deployments.forEach(d => { if (d.period) p.add(Number(d.period)) })
    return ['ALL', ...Array.from(p).sort((a,b) => a - b).map(n => String(n))]
  }, [deployments])

  const filtered = useMemo(() => {
    return deployments.filter(d => {
      const okP = periodSel === 'ALL' || String(d.period || '') === periodSel
      const okS = strengthSel === 'ALL' || String(d.strength || '') === strengthSel
      return okP && okS
    })
  }, [deployments, periodSel, strengthSel])

  const short = (id?: string) => {
    if (!id) return ''
    const e = names[String(id)]
    return e?.lastName || String(id)
  }
  const labelGroup = (arr?: string[]) => (arr || []).map(id => short(id)).join(' / ')

  const title = gameMeta ? `${gameMeta.away} @ ${gameMeta.home}` : `${opponent} vs ${teamId}`

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" onClick={onClose} />
      <motion.div initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 30, opacity: 0 }} className="relative bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl w-full max-w-5xl mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-sm font-military-display text-white uppercase tracking-wider">Head-to-Head — {opponent} • {title}{gameId ? ` • G${gameId}` : ''}</h4>
          <button onClick={onClose} className="text-[10px] font-military-display text-gray-400 hover:text-white uppercase tracking-wider">Close</button>
        </div>

        {loading && (
          <div className="text-xs text-gray-400 font-military-display">Loading deployments…</div>
        )}

        {!loading && (
          <>
            {/* Filters */}
            <div className="flex items-center space-x-3 mb-3">
              <div className="flex items-center space-x-2">
                <span className="text-[10px] text-gray-500 font-military-display uppercase">Period</span>
                <select value={periodSel} onChange={e => setPeriodSel(e.target.value)} className="bg-black/40 border border-white/10 rounded text-[11px] px-2 py-1 text-white">
                  {periods.map(p => (<option key={p} value={p}>{p}</option>))}
                </select>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-[10px] text-gray-500 font-military-display uppercase">Strength</span>
                <select value={strengthSel} onChange={e => setStrengthSel(e.target.value)} className="bg-black/40 border border-white/10 rounded text-[11px] px-2 py-1 text-white">
                  {strengths.map(s => (<option key={s} value={s}>{s}</option>))}
                </select>
              </div>
            </div>

            {/* Period Openers */}
            {periodOpeners && periodOpeners.length > 0 && (
              <div className="mb-3">
                <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Period Starters</div>
                <div className="rounded border bg-white/[0.02] border-white/5 divide-y divide-white/5 max-h-48 overflow-y-auto">
                  {periodOpeners.map((d, i) => (
                    <div key={`po-${i}`} className="p-2 text-[11px] font-military-display flex items-center justify-between">
                      <div className="text-gray-400">P{d.period} {mmss(((d?.whistle_time ?? d?.faceoff_time) != null && d?.period != null) ? ((d.whistle_time ?? d.faceoff_time) - ((d.period-1) * 1200)) : null)}</div>
                      <div className="text-gray-300">{d.away_forwards?.length ? labelGroup(d.away_forwards) : ''} {d.away_defense?.length ? ` | ${labelGroup(d.away_defense)}` : ''} <span className="text-gray-500 mx-2">@</span> {d.home_forwards?.length ? labelGroup(d.home_forwards) : ''} {d.home_defense?.length ? ` | ${labelGroup(d.home_defense)}` : ''}</div>
                      <div className="text-blue-400">{d.strength}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Whistle Deployments */}
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Whistle Deployments</div>
            <div className="rounded border bg-white/[0.02] border-white/5 max-h-96 overflow-y-auto">
              <div className="grid grid-cols-[0.8fr_2fr_2fr_0.8fr_0.8fr] gap-2 px-3 py-2 border-b border-white/10 text-[10px] text-gray-500">
                <div>Time</div>
                <div>{gameMeta?.away} On-Ice</div>
                <div>{gameMeta?.home} On-Ice</div>
                <div>Str</div>
                <div>Score</div>
              </div>
              {filtered.map((d, i) => (
                <div key={`dep-${i}`} className="grid grid-cols-[0.8fr_2fr_2fr_0.8fr_0.8fr] gap-2 px-3 py-2 border-b border-white/5 text-[11px] font-military-display">
                  <div className="text-gray-400">P{d.period} {mmss((d?.whistle_time != null && d?.period != null) ? (d.whistle_time - ((d.period-1) * 1200)) : null)}</div>
                  <div className="text-gray-300 truncate">{labelGroup(d.away_forwards)}{d.away_defense?.length ? ` | ${labelGroup(d.away_defense)}` : ''}</div>
                  <div className="text-gray-300 truncate">{labelGroup(d.home_forwards)}{d.home_defense?.length ? ` | ${labelGroup(d.home_defense)}` : ''}</div>
                  <div className="text-blue-400">{d.strength}</div>
                  <div className="text-white tabular-nums">{d.home_score ?? '-'}-{d.away_score ?? '-'}</div>
                </div>
              ))}
              {filtered.length === 0 && (
                <div className="px-3 py-4 text-[11px] text-gray-500">No deployments match filters.</div>
              )}
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  )
}

