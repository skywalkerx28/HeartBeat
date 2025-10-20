'use client'

import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  fetchTeamRotations,
  fetchTeamRotationTransitions,
  TeamRotationEvent,
  TeamRotationTransitionAgg,
  resolvePlayerNames,
  PlayerNameEntry,
} from '../../lib/profileApi'

type StrengthFilter = '5v5' | '5v4' | '4v5' | 'all'

interface Props { teamId: string; season?: string }

function parseLineKey(line: string | undefined | null) {
  if (!line) return { f: [] as string[], d: [] as string[] }
  const parts = String(line).split('_')
  const f = parts.find(p => p.startsWith('F:'))?.slice(2) || ''
  const d = parts.find(p => p.startsWith('D:'))?.slice(2) || ''
  return {
    f: f ? f.split('|').filter(Boolean) : [],
    d: d ? d.split('|').filter(Boolean) : [],
  }
}

function shortName(entry?: PlayerNameEntry) {
  if (!entry) return undefined
  const last = entry.lastName || ''
  const first = entry.firstName ? entry.firstName[0] + '.' : ''
  return `${first ? first + ' ' : ''}${last}`
}

export function TeamRotationAnalytics({ teamId, season }: Props) {
  const [strength, setStrength] = useState<StrengthFilter>('5v5')
  const [events, setEvents] = useState<TeamRotationEvent[]>([])
  const [transitions, setTransitions] = useState<TeamRotationTransitionAgg[]>([])
  const [perGameTransitions, setPerGameTransitions] = useState<TeamRotationTransitionAgg[]>([])
  const [seasonSel, setSeasonSel] = useState<string | undefined>(season)
  const [seasonOptions, setSeasonOptions] = useState<string[]>([])
  const [groupMode, setGroupMode] = useState<'overall' | 'perGame'>('overall')
  const [opponents, setOpponents] = useState<string[]>([])
  const [oppSel, setOppSel] = useState<string | undefined>(undefined)
  const [nameMap, setNameMap] = useState<Record<string, PlayerNameEntry>>({})
  const [loading, setLoading] = useState<boolean>(true)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      try {
        const strengthParam = strength === 'all'
          ? undefined
          : strength === '5v5'
            ? 'evenStrength'
            : strength === '5v4'
              ? 'powerPlay'
              : strength === '4v5'
                ? 'shortHanded'
                : undefined
        const [rot, trans, transGame] = await Promise.all([
          fetchTeamRotations({ team: teamId, season: seasonSel, strength: strengthParam, limit: 300, opponent: oppSel }),
          fetchTeamRotationTransitions({ team: teamId, season: seasonSel, strength: strengthParam, limit: 50 }),
          fetchTeamRotationTransitions({ team: teamId, season: seasonSel, strength: strengthParam, limit: 200, groupBy: 'game', opponent: oppSel }),
        ])
        if (cancelled) return
        setEvents(rot.events || [])
        setTransitions(trans.transitions || [])
        setPerGameTransitions(transGame.transitions || [])

        const seasons = Array.from(new Set<string>(
          [
            ...(trans.transitions || []).map((t: any) => String(t.season || '')).filter(Boolean),
            ...(rot.events || []).map((e: any) => String(e.season || '')).filter(Boolean),
            ...(transGame.transitions || []).map((t: any) => String(t.season || '')).filter(Boolean),
          ]
        ))
          .filter(Boolean)
          .sort()
          .reverse()
        setSeasonOptions(seasons)
        if (!seasonSel && seasons.length) setSeasonSel(seasons[0])

        const opps = Array.from(new Set((transGame.transitions || []).map((t: any) => String(t.opponent || '')).filter(Boolean))).sort()
        setOpponents(opps)

        const ids = new Set<string>()
        for (const e of rot.events || []) {
          const add = (pipe?: string | null) => {
            if (!pipe) return
            pipe.split('|').forEach(x => x && ids.add(String(x)))
          }
          add(e.from_forwards as any)
          add(e.from_defense as any)
          add(e.to_forwards as any)
          add(e.to_defense as any)
          for (const r of (e.replacements_f || [])) {
            if (r.out) ids.add(String(r.out))
            if (r.in) ids.add(String(r.in))
          }
          for (const r of (e.replacements_d || [])) {
            if (r.out) ids.add(String(r.out))
            if (r.in) ids.add(String(r.in))
          }
        }
        for (const t of trans.transitions || []) {
          const p1 = parseLineKey(t.from_line)
          const p2 = parseLineKey(t.to_line)
          ;[...p1.f, ...p1.d, ...p2.f, ...p2.d].forEach(x => x && ids.add(String(x)))
        }
        if (ids.size) {
          const map = await resolvePlayerNames(Array.from(ids))
          if (!cancelled) setNameMap(map || {})
        }
      } catch (e) {
        console.error('Rotation fetch failed', e)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [teamId, seasonSel, strength, oppSel])

  const topTransitions = useMemo(() => transitions.slice(0, 12), [transitions])
  const perGameTop = useMemo(() => perGameTransitions.slice(0, 20), [perGameTransitions])
  const recentEvents = useMemo(() => events.slice(-25).reverse(), [events])

  const strengthOptions: StrengthFilter[] = ['5v5', '5v4', '4v5', 'all']

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-lg"
    >
      <div className="absolute inset-0 bg-black/40 backdrop-blur-xl border border-white/10" />
      <div className="relative p-6">
        {/* Header with title and filters */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
              <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                Line Rotation Patterns
              </h3>
            </div>
          </div>

          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Strength Filter */}
            <div className="flex items-center space-x-1">
              <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider mr-2">Strength</span>
              {strengthOptions.map(s => (
                <button
                  key={s}
                  onClick={() => setStrength(s)}
                  className={`px-2 py-1 rounded border text-[10px] font-military-display transition-all ${
                    strength === s 
                      ? 'bg-red-600/10 border-red-600/30 text-red-400' 
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white hover:border-white/20'
                  }`}
                >
                  {s.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Season Selector */}
            {seasonOptions.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Season</span>
                <select
                  className="bg-white/5 text-gray-300 border border-white/10 rounded px-2 py-1 text-[10px] font-military-display hover:bg-white/10 transition-all focus:outline-none focus:border-white/20"
                  value={seasonSel || ''}
                  onChange={e => setSeasonSel(e.target.value || undefined)}
                >
                  {seasonOptions.map(s => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Group Mode */}
            <div className="flex items-center space-x-2">
              <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">View</span>
              <div className="inline-flex">
                <button
                  onClick={() => setGroupMode('overall')}
                  className={`px-2 py-1 rounded-l border text-[10px] font-military-display transition-all ${
                    groupMode==='overall' 
                      ? 'bg-white/10 border-white/30 text-white' 
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  OVERALL
                </button>
                <button
                  onClick={() => setGroupMode('perGame')}
                  className={`px-2 py-1 rounded-r border-l-0 border text-[10px] font-military-display transition-all ${
                    groupMode==='perGame' 
                      ? 'bg-white/10 border-white/30 text-white' 
                      : 'bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:text-white'
                  }`}
                >
                  PER GAME
                </button>
              </div>
            </div>

            {/* Opponent Selector */}
            {opponents.length > 0 && (
              <div className="flex items-center space-x-2">
                <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Opponent</span>
                <select
                  className="bg-white/5 text-gray-300 border border-white/10 rounded px-2 py-1 text-[10px] font-military-display hover:bg-white/10 transition-all focus:outline-none focus:border-white/20"
                  value={oppSel || ''}
                  onChange={e => setOppSel(e.target.value || undefined)}
                >
                  <option value="">All Teams</option>
                  {opponents.map(o => (
                    <option key={o} value={o}>{o}</option>
                  ))}
                </select>
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-1 gap-6">
          {/* Top Transitions */}
          <div className="rounded-lg border border-white/5 bg-white/[0.02] overflow-hidden">
            <div className="px-4 py-2 border-b border-white/10 bg-white/[0.02]">
              <h4 className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
                {groupMode==='overall' ? 'Top Transitions' : 'Recent Game Transitions'} ({strength.toUpperCase()})
              </h4>
            </div>
            <div className="divide-y divide-white/5">
              {(groupMode==='overall' ? topTransitions : perGameTop.filter(t => !oppSel || t.opponent === oppSel)).map((t, i) => {
                const from = parseLineKey(t.from_line)
                const to = parseLineKey(t.to_line)
                const label = (ids: string[]) => ids.map(id => shortName(nameMap[id]) || id).join(' / ')
                return (
                  <motion.div 
                    key={`${t.from_line}->${t.to_line}-${t.game_id ?? 'all'}-${i}`}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.05 + i * 0.02 }}
                    className="p-4 hover:bg-white/[0.02] transition-all"
                  >
                    {/* Game Info (Per Game Mode) */}
                    {t.game_id && (
                      <div className="flex items-center space-x-3 mb-3 text-[10px] font-military-display">
                        <span className="text-gray-500">{String(t.game_id).slice(0, 10)}</span>
                        {t.game_date && <span className="text-gray-600">•</span>}
                        {t.game_date && <span className="text-gray-500">{t.game_date}</span>}
                        {t.opponent && (
                          <>
                            <span className="text-gray-600">•</span>
                            <span className="text-gray-400">vs {t.opponent}</span>
                          </>
                        )}
                        {t.result && (
                          <>
                            <span className="text-gray-600">•</span>
                            <span className={`${t.result === 'W' ? 'text-white' : t.result === 'L' ? 'text-red-400' : 'text-gray-400'}`}>
                              {t.result}
                            </span>
                          </>
                        )}
                      </div>
                    )}

                    {/* FROM Line */}
                    <div className="mb-3">
                      <div className="flex items-start space-x-3">
                        <div className="w-12 text-[9px] font-military-display text-gray-600 uppercase tracking-wider pt-0.5">From</div>
                        <div className="flex-1 space-y-1">
                          <div className="text-xs font-military-display">
                            <span className="text-gray-500">F:</span>
                            <span className="text-white ml-2">{label(from.f) || '—'}</span>
                          </div>
                          <div className="text-xs font-military-display">
                            <span className="text-gray-500">D:</span>
                            <span className="text-white ml-2">{label(from.d) || '—'}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Arrow */}
                    <div className="flex items-center space-x-3 my-2">
                      <div className="w-12"></div>
                      <div className="flex-1">
                        <div className="text-gray-600 text-xs">→</div>
                      </div>
                    </div>

                    {/* TO Line */}
                    <div className="mb-3">
                      <div className="flex items-start space-x-3">
                        <div className="w-12 text-[9px] font-military-display text-gray-600 uppercase tracking-wider pt-0.5">To</div>
                        <div className="flex-1 space-y-1">
                          <div className="text-xs font-military-display">
                            <span className="text-gray-500">F:</span>
                            <span className="text-white ml-2">{label(to.f) || '—'}</span>
                          </div>
                          <div className="text-xs font-military-display">
                            <span className="text-gray-500">D:</span>
                            <span className="text-white ml-2">{label(to.d) || '—'}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Count Badge */}
                    <div className="flex items-center space-x-3 mt-3 pt-3 border-t border-white/5">
                      <div className="w-12"></div>
                      <div className="flex-1">
                        <div className="inline-flex items-center space-x-2 px-2 py-1 rounded bg-white/5 border border-white/10">
                          <span className="text-[9px] font-military-display text-gray-500 uppercase tracking-wider">Count</span>
                          <span className="text-xs font-military-display text-white tabular-nums">{t.count}</span>
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
              {((groupMode==='overall' ? topTransitions : perGameTop).length === 0) && (
                <div className="p-8 text-center text-xs font-military-display text-gray-500">
                  NO TRANSITIONS FOUND FOR SELECTED FILTERS
                </div>
              )}
            </div>
          </div>

          {/* Recent Rotation Events */}
          <div className="rounded-lg border border-white/5 bg-white/[0.02] overflow-hidden">
            <div className="px-4 py-2 border-b border-white/10 bg-white/[0.02]">
              <h4 className="text-[10px] font-military-display text-gray-400 uppercase tracking-wider">
                Recent Rotation Events ({strength.toUpperCase()})
              </h4>
            </div>
            <div className="divide-y divide-white/5 max-h-96 overflow-y-auto">
              {recentEvents.map((e, i) => {
                const fromLine = `F:${e.from_forwards || ''}_D:${e.from_defense || ''}`
                const toLine = `F:${e.to_forwards || ''}_D:${e.to_defense || ''}`
                const fromParsed = parseLineKey(fromLine)
                const toParsed = parseLineKey(toLine)
                return (
                <motion.div 
                  key={`${e.game_id}-${e.sequence_index}-${i}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 + i * 0.01 }}
                  className="p-4 hover:bg-white/[0.02] transition-all"
                >
                  {/* Event Header */}
                  <div className="flex items-center space-x-3 mb-3 text-[10px] font-military-display">
                    <span className="text-white">GAME {String(e.game_id)}</span>
                    {e.period !== null && e.period !== undefined && (
                      <>
                        <span className="text-gray-600">•</span>
                        <span className="text-gray-400">P{e.period}</span>
                      </>
                    )}
                    {e.period_time !== undefined && e.period_time !== null && (
                      <>
                        <span className="text-gray-600">•</span>
                        <span className="text-gray-400">{typeof e.period_time === 'number' ? e.period_time.toFixed(0) : e.period_time}s</span>
                      </>
                    )}
                    {e.strength_state && (
                      <>
                        <span className="text-gray-600">•</span>
                        <span className="text-gray-500">{e.strength_state}</span>
                      </>
                    )}
                    {typeof e.score_differential === 'number' && (
                      <>
                        <span className="text-gray-600">•</span>
                        <span className={`${e.score_differential > 0 ? 'text-white' : e.score_differential < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                          {e.score_differential >= 0 ? `+${e.score_differential}` : e.score_differential}
                        </span>
                      </>
                    )}
                  </div>

                  {/* FROM Line */}
                  <div className="mb-2 space-y-1">
                    <div className="text-xs font-military-display">
                      <span className="text-gray-500">FROM F:</span>
                      <span className="text-white ml-2">{fromParsed.f.map(id => shortName(nameMap[id]) || id).join(' / ') || '—'}</span>
                    </div>
                    <div className="text-xs font-military-display">
                      <span className="text-gray-500">FROM D:</span>
                      <span className="text-white ml-2">{fromParsed.d.map(id => shortName(nameMap[id]) || id).join(' / ') || '—'}</span>
                    </div>
                  </div>

                  {/* Arrow */}
                  <div className="text-gray-600 text-xs my-2 ml-16">→</div>

                  {/* TO Line */}
                  <div className="mb-3 space-y-1">
                    <div className="text-xs font-military-display">
                      <span className="text-gray-500">TO F:</span>
                      <span className="text-white ml-2">{toParsed.f.map(id => shortName(nameMap[id]) || id).join(' / ') || '—'}</span>
                    </div>
                    <div className="text-xs font-military-display">
                      <span className="text-gray-500">TO D:</span>
                      <span className="text-white ml-2">{toParsed.d.map(id => shortName(nameMap[id]) || id).join(' / ') || '—'}</span>
                    </div>
                  </div>

                  {/* Replacements */}
                  {(e.replacements_f && e.replacements_f.length > 0) || (e.replacements_d && e.replacements_d.length > 0) ? (
                    <div className="mt-3 pt-3 border-t border-white/5 space-y-1">
                      {e.replacements_f && e.replacements_f.length > 0 && (
                        <div className="text-[10px] font-military-display">
                          <span className="text-gray-500">F CHANGES:</span>
                          {e.replacements_f.map((r, idx) => (
                            <span key={idx} className="ml-3 text-white">
                              {shortName(nameMap[String(r.out || '')]) || r.out || '—'}
                              <span className="text-gray-600 mx-1">→</span>
                              {shortName(nameMap[String(r.in || '')]) || r.in || '—'}
                            </span>
                          ))}
                        </div>
                      )}
                      {e.replacements_d && e.replacements_d.length > 0 && (
                        <div className="text-[10px] font-military-display">
                          <span className="text-gray-500">D CHANGES:</span>
                          {e.replacements_d.map((r, idx) => (
                            <span key={idx} className="ml-3 text-white">
                              {shortName(nameMap[String(r.out || '')]) || r.out || '—'}
                              <span className="text-gray-600 mx-1">→</span>
                              {shortName(nameMap[String(r.in || '')]) || r.in || '—'}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : null}
                </motion.div>
                )
              })}
              {(!recentEvents || recentEvents.length === 0) && (
                <div className="p-8 text-center text-xs font-military-display text-gray-500">
                  NO ROTATION EVENTS FOUND FOR SELECTED FILTERS
                </div>
              )}
            </div>
          </div>
        </div>

        {loading && (
          <div className="mt-4 text-[10px] text-gray-500 font-military-display text-center">
            LOADING ROTATION DATA...
          </div>
        )}
      </div>
    </motion.div>
  )}
