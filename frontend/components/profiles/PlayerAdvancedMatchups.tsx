'use client'

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { AdvancedPlayerMetrics, resolvePlayerNames, PlayerNameEntry } from '../../lib/profileApi'

interface PlayerAdvancedMatchupsProps {
  adv: AdvancedPlayerMetrics
}

function secondsToMinStr(sec: number): string {
  if (!sec || sec <= 0) return '0.0'
  return (sec / 60).toFixed(1)
}

export function PlayerAdvancedMatchups({ adv }: PlayerAdvancedMatchupsProps) {
  const totals = adv.totals

  // Top 5 opponents by time
  const topOppByTime = (totals.top_opponents_by_time || []).slice(0, 5)

  // Top 5 opponents by appearances
  const oppAppsEntries = Object.entries(totals.opponent_appearances || {}) as Array<[string, number]>
  const topOppByApps = oppAppsEntries
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)

  // Top 3 trios by time
  const trioTimeEntries = Object.entries(totals.trio_time_sec || {}) as Array<[string, number]>
  const topTriosByTime = trioTimeEntries
    .sort((a, b) => (b[1] || 0) - (a[1] || 0))
    .slice(0, 3)

  // Line vs Pair and Pair vs Line (show top 5)
  const lvpEntries = Object.entries(totals.line_vs_pair_appearances || {}) as Array<[string, number]>
  const topLineVsPair = lvpEntries.sort((a, b) => b[1] - a[1]).slice(0, 5)
  const pvlEntries = Object.entries(totals.pair_vs_line_appearances || {}) as Array<[string, number]>
  const topPairVsLine = pvlEntries.sort((a, b) => b[1] - a[1]).slice(0, 5)

  const deployments = totals.deployments || { count: 0, by_zone: {}, by_strength: {}, faceoff_zone: {} }

  // Resolve player IDs -> last names (only IDs that appear in these top lists)
  const idsToResolve = useMemo(() => {
    const ids = new Set<string>()
    // Opponent ids
    topOppByTime.forEach(o => { if (o?.opponent_id) ids.add(String(o.opponent_id)) })
    topOppByApps.forEach(([pid]) => ids.add(String(pid)))
    // Trios (parse tuples)
    topTriosByTime.forEach(([trio]) => {
      const inner = trio.replace(/^\(/, '').replace(/\)$/, '')
      inner.split(',').forEach(p => {
        const id = p.trim().replace(/['"]/g, '')
        if (id) ids.add(id)
      })
    })
    // Line vs Pair & Pair vs Line
    topLineVsPair.forEach(([pairKey]) => {
      const inner = pairKey.replace(/^\(/, '').replace(/\)$/, '')
      inner.split(',').forEach(p => { const id = p.trim().replace(/['"]/g, ''); if (id) ids.add(id) })
    })
    topPairVsLine.forEach(([lineKey]) => {
      const inner = lineKey.replace(/^\(/, '').replace(/\)$/, '')
      inner.split(',').forEach(p => { const id = p.trim().replace(/['"]/g, ''); if (id) ids.add(id) })
    })
    return Array.from(ids)
  }, [topOppByTime, topOppByApps, topTriosByTime, topLineVsPair, topPairVsLine])

  // Stable key to avoid repeated resolves on identical contents
  const idsKey = useMemo(() => idsToResolve.slice().sort().join(','), [idsToResolve])

  const [nameMap, setNameMap] = useState<Record<string, PlayerNameEntry>>({})

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      if (!idsKey) return
      if (idsToResolve.length === 0) return
      // If all ids are already present in map, skip
      const allHave = idsToResolve.every(id => nameMap[String(id)])
      if (allHave) return
      const resolved = await resolvePlayerNames(idsToResolve)
      if (!cancelled && resolved) {
        setNameMap(prev => ({ ...prev, ...resolved }))
      }
    })()
    return () => { cancelled = true }
  }, [idsKey])

  const shortName = (id: string | number) => {
    const key = String(id)
    const entry = nameMap[key]
    return entry?.lastName || key
  }

  const formatIdTuple = (tupleStr: string, sep = ' / ') => {
    const inner = tupleStr.replace(/^\(/, '').replace(/\)$/, '')
    const ids = inner.split(',').map(s => s.trim().replace(/['"]/g, '')).filter(Boolean)
    const names = ids.map(shortName)
    return names.join(sep)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-lg"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        <div className="flex items-center space-x-2 mb-4">
          <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
          <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
            Matchups & Deployments
          </h3>
        </div>

        {/* Opponents */}
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
              Top Opponents by Time (min)
            </div>
            <div className="space-y-1.5">
              {topOppByTime.map((o, idx) => (
                <div key={idx} className="flex items-center justify-between text-sm font-military-display">
                  <span className="text-gray-400 truncate">{shortName(o.opponent_id)}</span>
                  <span className="text-white tabular-nums">{secondsToMinStr(o.total_time_sec)}</span>
                </div>
              ))}
              {topOppByTime.length === 0 && (
                <div className="text-xs text-gray-500 font-military-display">No data</div>
              )}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
              Top Opponents by Appearances
            </div>
            <div className="space-y-1.5">
              {topOppByApps.map(([pid, cnt]) => (
                <div key={pid} className="flex items-center justify-between text-sm font-military-display">
                  <span className="text-gray-400 truncate">{shortName(pid)}</span>
                  <span className="text-white tabular-nums">{cnt}</span>
                </div>
              ))}
              {topOppByApps.length === 0 && (
                <div className="text-xs text-gray-500 font-military-display">No data</div>
              )}
            </div>
          </div>
        </div>

        {/* Trios */}
        <div className="mb-4">
          <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
            Top Trios by Time (min)
          </div>
          <div className="space-y-1.5">
            {topTriosByTime.map(([trio, secs]) => (
              <div key={trio} className="flex items-center justify-between text-sm font-military-display">
                <span className="text-gray-400 truncate">{formatIdTuple(trio, ' • ')}</span>
                <span className="text-white tabular-nums">{secondsToMinStr(secs)}</span>
              </div>
            ))}
            {topTriosByTime.length === 0 && (
              <div className="text-xs text-gray-500 font-military-display">No data</div>
            )}
          </div>
        </div>

        {/* Line/Pair summaries */}
        <div className="grid grid-cols-2 gap-6 mb-4">
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
              Line vs Pair (Appearances)
            </div>
            <div className="space-y-1.5">
              {topLineVsPair.map(([pairKey, cnt]) => (
                <div key={pairKey} className="flex items-center justify-between text-sm font-military-display">
                  <span className="text-gray-400 truncate">{formatIdTuple(pairKey)}</span>
                  <span className="text-white tabular-nums">{cnt}</span>
                </div>
              ))}
              {topLineVsPair.length === 0 && (
                <div className="text-xs text-gray-500 font-military-display">No data</div>
              )}
            </div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
              Pair vs Line (Appearances)
            </div>
            <div className="space-y-1.5">
              {topPairVsLine.map(([lineKey, cnt]) => (
                <div key={lineKey} className="flex items-center justify-between text-sm font-military-display">
                  <span className="text-gray-400 truncate">{formatIdTuple(lineKey)}</span>
                  <span className="text-white tabular-nums">{cnt}</span>
                </div>
              ))}
              {topPairVsLine.length === 0 && (
                <div className="text-xs text-gray-500 font-military-display">No data</div>
              )}
            </div>
          </div>
        </div>

        {/* Deployments */}
        <div>
          <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">
            Deployments (Zone Starts & Strength)
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Zone Starts</div>
              <div className="space-y-1">
                {Object.entries(deployments.by_zone || {}).map(([z, c]) => (
                  <div key={z} className="flex items-center justify-between text-sm font-military-display">
                    <span className="text-gray-400 uppercase">{z}</span>
                    <span className="text-white tabular-nums">{c as number}</span>
                  </div>
                ))}
                {(!deployments.by_zone || Object.keys(deployments.by_zone).length === 0) && (
                  <div className="text-xs text-gray-500 font-military-display">No data</div>
                )}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Strength</div>
              <div className="space-y-1">
                {Object.entries(deployments.by_strength || {}).map(([s, c]) => (
                  <div key={s} className="flex items-center justify-between text-sm font-military-display">
                    <span className="text-gray-400 uppercase">{s}</span>
                    <span className="text-white tabular-nums">{c as number}</span>
                  </div>
                ))}
                {(!deployments.by_strength || Object.keys(deployments.by_strength).length === 0) && (
                  <div className="text-xs text-gray-500 font-military-display">No data</div>
                )}
              </div>
            </div>
            <div>
              <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Faceoff Zone</div>
              <div className="space-y-1">
                {Object.entries(deployments.faceoff_zone || {}).map(([z, c]) => (
                  <div key={z} className="flex items-center justify-between text-sm font-military-display">
                    <span className="text-gray-400 uppercase">{z}</span>
                    <span className="text-white tabular-nums">{c as number}</span>
                  </div>
                ))}
                {(!deployments.faceoff_zone || Object.keys(deployments.faceoff_zone).length === 0) && (
                  <div className="text-xs text-gray-500 font-military-display">No data</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  )
}
