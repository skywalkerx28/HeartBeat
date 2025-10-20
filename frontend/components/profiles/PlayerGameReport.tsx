'use client'

import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AdvancedPlayerMetrics } from '../../lib/profileApi'

interface PlayerGameReportProps {
  adv: AdvancedPlayerMetrics
}

function toMMSS(sec?: number | null): string {
  if (sec == null || isNaN(Number(sec))) return '--:--'
  const s = Math.max(0, Math.round(Number(sec)))
  const m = Math.floor(s / 60)
  const r = s % 60
  return `${String(m).padStart(2, '0')}:${String(r).padStart(2, '0')}`
}

export function PlayerGameReport({ adv }: PlayerGameReportProps) {
  const [open, setOpen] = React.useState(false)

  const latest = React.useMemo(() => {
    const games = (adv.games || []) as any[]
    if (!games.length) return null
    // Prefer latest by gameDate, fallback to last item
    const withDates = games.filter(g => !!g.gameDate)
    if (withDates.length) {
      return withDates.slice().sort((a,b) => new Date(b.gameDate).getTime() - new Date(a.gameDate).getTime())[0]
    }
    return games[games.length - 1]
  }, [adv])

  if (!latest) return null

  const title = `${latest.awayTeam || ''} @ ${latest.homeTeam || ''}`.trim()
  const dateStr = latest.gameDate ? new Date(latest.gameDate).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : ''

  const entries = latest.entries || {}
  const exits = latest.exits || {}

  const clipsPlaceholder = [
    { label: 'Top Sequence', note: 'Clip coming soon' },
    { label: 'Best OZ Entry', note: 'Clip coming soon' },
    { label: 'Key Defensive Play', note: 'Clip coming soon' },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="relative overflow-hidden rounded-lg">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-2">
            <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
            <h3 className="text-xs font-military-display text-white uppercase tracking-widest">Game Report</h3>
          </div>
          <button onClick={() => setOpen(true)} className="text-[10px] font-military-display text-red-400 hover:text-red-300 uppercase tracking-wider">Open</button>
        </div>

        <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Latest Game</div>
        <div className="text-sm font-military-display text-white">{title}</div>
        <div className="text-[10px] font-military-display text-gray-500">{dateStr}</div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Shifts</div>
            <div className="text-base font-military-display text-white tabular-nums">{latest.shift_count ?? 0}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">TOI (game)</div>
            <div className="text-base font-military-display text-white tabular-nums">{toMMSS(latest.toi_game_sec)}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Avg Shift</div>
            <div className="text-base font-military-display text-white tabular-nums">{toMMSS(latest.avg_shift_game_sec)}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Avg Rest</div>
            <div className="text-base font-military-display text-white tabular-nums">{toMMSS(latest.avg_rest_game_sec)}</div>
          </div>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Entries Ctrl</div>
            <div className="text-sm font-military-display text-white tabular-nums">{Number(entries.controlled_success || 0)}/{Number(entries.controlled_attempts || 0)}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Exits Ctrl</div>
            <div className="text-sm font-military-display text-white tabular-nums">{Number(exits.controlled_success || 0)}/{Number(exits.controlled_attempts || 0)}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">LPR Rec</div>
            <div className="text-sm font-military-display text-white tabular-nums">{latest.lpr_recoveries ?? 0}</div>
          </div>
          <div>
            <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-1">Pressure</div>
            <div className="text-sm font-military-display text-white tabular-nums">{latest.pressure_events ?? 0}</div>
          </div>
        </div>

        {/* Modal */}
        <AnimatePresence>
          {open && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center">
              <div className="absolute inset-0 bg-black/70" onClick={() => setOpen(false)} />
              <motion.div initial={{ y: 30, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 30, opacity: 0 }} className="relative bg-gray-900/95 backdrop-blur-xl border border-white/10 rounded-lg shadow-2xl w-full max-w-3xl mx-4 p-6">
                <div className="flex items-center justify-between mb-4">
                  <h4 className="text-sm font-military-display text-white uppercase tracking-wider">{title} — {dateStr}</h4>
                  <button onClick={() => setOpen(false)} className="text-[10px] font-military-display text-gray-400 hover:text-white uppercase tracking-wider">Close</button>
                </div>
                <div className="grid grid-cols-2 gap-6">
                  <div>
                    <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">Summary</div>
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">Shifts</span><span className="text-white tabular-nums">{latest.shift_count ?? 0}</span></div>
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">TOI</span><span className="text-white tabular-nums">{toMMSS(latest.toi_game_sec)}</span></div>
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">Avg Shift</span><span className="text-white tabular-nums">{toMMSS(latest.avg_shift_game_sec)}</span></div>
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">Avg Rest</span><span className="text-white tabular-nums">{toMMSS(latest.avg_rest_game_sec)}</span></div>
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">Entries Ctrl</span><span className="text-white tabular-nums">{Number(entries.controlled_success || 0)}/{Number(entries.controlled_attempts || 0)}</span></div>
                      <div className="flex items-center justify-between text-sm font-military-display"><span className="text-gray-400">Exits Ctrl</span><span className="text-white tabular-nums">{Number(exits.controlled_success || 0)}/{Number(exits.controlled_attempts || 0)}</span></div>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] font-military-display text-gray-500 uppercase tracking-wider mb-2">Clips Recap</div>
                    <div className="space-y-1.5">
                      {clipsPlaceholder.map((c, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm font-military-display">
                          <span className="text-gray-400">{c.label}</span>
                          <span className="text-gray-600">{c.note}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  )
}

