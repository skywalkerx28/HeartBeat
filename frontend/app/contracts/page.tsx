'use client'

import React, { useState, useEffect, useMemo } from 'react'
import { motion } from 'framer-motion'
import { BasePage } from '../../components/layout/BasePage'
import { 
  ClockIcon,
  CurrencyDollarIcon,
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  ChartBarIcon,
  TrophyIcon,
  BellAlertIcon,
  ChevronDownIcon
} from '@heroicons/react/24/outline'
import { getTeamContracts, getTeamCapSummary, getTeamDepthChart, DepthChartPlayer, getPlayerContract, getPlayerContractByName } from '../../lib/marketApi'
import { ContractTimeline } from '../../components/contracts/ContractTimeline'
import { RosterContractList } from '../../components/contracts/RosterContractList'
import { ActivityFeed } from '../../components/contracts/ActivityFeed'
import { ContractTicker } from '../../components/contracts/ContractTicker'

interface PlayerContract {
  playerId: string
  playerName: string
  position: string
  age: number
  capHit: number
  yearsRemaining: number
  contractType: string
  rosterStatus: string
  contractStatus?: string
  deadCap?: boolean
  expiryYear?: string
  capHitPercentage?: number
  noTradeClause?: boolean
  noMovementClause?: boolean
  baseSalary?: number
  signingBonus?: number
  // Depth chart enrichment fields
  jerseyNumber?: number
  birthDate?: string
  birthCountry?: string
  heightInches?: number
  weightPounds?: number
  shootsCatches?: string
  headshot?: string
}

const NHL_TEAMS = [
  { abbrev: 'ANA', name: 'ANAHEIM DUCKS', division: 'Pacific', ahl: 'San Diego Gulls' },
  { abbrev: 'BOS', name: 'BOSTON BRUINS', division: 'Atlantic', ahl: 'Providence Bruins' },
  { abbrev: 'BUF', name: 'BUFFALO SABRES', division: 'Atlantic', ahl: 'Rochester Americans' },
  { abbrev: 'CAR', name: 'CAROLINA HURRICANES', division: 'Metropolitan', ahl: 'Chicago Wolves' },
  { abbrev: 'CBJ', name: 'COLUMBUS BLUE JACKETS', division: 'Metropolitan', ahl: 'Cleveland Monsters' },
  { abbrev: 'CGY', name: 'CALGARY FLAMES', division: 'Pacific', ahl: 'Calgary Wranglers' },
  { abbrev: 'CHI', name: 'CHICAGO BLACKHAWKS', division: 'Central', ahl: 'Rockford IceHogs' },
  { abbrev: 'COL', name: 'COLORADO AVALANCHE', division: 'Central', ahl: 'Colorado Eagles' },
  { abbrev: 'DAL', name: 'DALLAS STARS', division: 'Central', ahl: 'Texas Stars' },
  { abbrev: 'DET', name: 'DETROIT RED WINGS', division: 'Atlantic', ahl: 'Grand Rapids Griffins' },
  { abbrev: 'EDM', name: 'EDMONTON OILERS', division: 'Pacific', ahl: 'Bakersfield Condors' },
  { abbrev: 'FLA', name: 'FLORIDA PANTHERS', division: 'Atlantic', ahl: 'Charlotte Checkers' },
  { abbrev: 'LAK', name: 'LOS ANGELES KINGS', division: 'Pacific', ahl: 'Ontario Reign' },
  { abbrev: 'MIN', name: 'MINNESOTA WILD', division: 'Central', ahl: 'Iowa Wild' },
  { abbrev: 'MTL', name: 'MONTREAL CANADIENS', division: 'Atlantic', ahl: 'Laval Rocket' },
  { abbrev: 'NJD', name: 'NEW JERSEY DEVILS', division: 'Metropolitan', ahl: 'Utica Comets' },
  { abbrev: 'NSH', name: 'NASHVILLE PREDATORS', division: 'Central', ahl: 'Milwaukee Admirals' },
  { abbrev: 'NYI', name: 'NEW YORK ISLANDERS', division: 'Metropolitan', ahl: 'Bridgeport Islanders' },
  { abbrev: 'NYR', name: 'NEW YORK RANGERS', division: 'Metropolitan', ahl: 'Hartford Wolf Pack' },
  { abbrev: 'OTT', name: 'OTTAWA SENATORS', division: 'Atlantic', ahl: 'Belleville Senators' },
  { abbrev: 'PHI', name: 'PHILADELPHIA FLYERS', division: 'Metropolitan', ahl: 'Lehigh Valley Phantoms' },
  { abbrev: 'PIT', name: 'PITTSBURGH PENGUINS', division: 'Metropolitan', ahl: 'Wilkes-Barre/Scranton Penguins' },
  { abbrev: 'SEA', name: 'SEATTLE KRAKEN', division: 'Pacific', ahl: 'Coachella Valley Firebirds' },
  { abbrev: 'SJS', name: 'SAN JOSE SHARKS', division: 'Pacific', ahl: 'San Jose Barracuda' },
  { abbrev: 'STL', name: 'ST. LOUIS BLUES', division: 'Central', ahl: 'Springfield Thunderbirds' },
  { abbrev: 'TBL', name: 'TAMPA BAY LIGHTNING', division: 'Atlantic', ahl: 'Syracuse Crunch' },
  { abbrev: 'TOR', name: 'TORONTO MAPLE LEAFS', division: 'Atlantic', ahl: 'Toronto Marlies' },
  { abbrev: 'UTA', name: 'UTAH HOCKEY CLUB', division: 'Central', ahl: 'Tucson Roadrunners' },
  { abbrev: 'VAN', name: 'VANCOUVER CANUCKS', division: 'Pacific', ahl: 'Abbotsford Canucks' },
  { abbrev: 'VGK', name: 'VEGAS GOLDEN KNIGHTS', division: 'Pacific', ahl: 'Henderson Silver Knights' },
  { abbrev: 'WPG', name: 'WINNIPEG JETS', division: 'Central', ahl: 'Manitoba Moose' },
  { abbrev: 'WSH', name: 'WASHINGTON CAPITALS', division: 'Metropolitan', ahl: 'Hershey Bears' },
]

export default function ContractsTerminalPage() {
  const [currentTime, setCurrentTime] = useState('')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const [contracts, setContracts] = useState<PlayerContract[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedTeam] = useState('MTL')

  // Independent selectors for left and right columns
  const [leftTeam, setLeftTeam] = useState('MTL')
  const [rightTeam, setRightTeam] = useState('MTL')
  const [isLeftTeamDropdownOpen, setIsLeftTeamDropdownOpen] = useState(false)
  const [isRightTeamDropdownOpen, setIsRightTeamDropdownOpen] = useState(false)
  const getTeamInfo = (abbrev: string) => NHL_TEAMS.find(t => t.abbrev === abbrev)
  const [leftTitleName, setLeftTitleName] = useState<string>(getTeamInfo('MTL')?.name || 'MONTREAL CANADIENS')
  const [rightTitleName, setRightTitleName] = useState<string>(getTeamInfo('MTL')?.name || 'MONTREAL CANADIENS')
  const [leftRosterType, setLeftRosterType] = useState<'NHL' | 'AHL'>('AHL')
  const [rightRosterType, setRightRosterType] = useState<'NHL' | 'AHL'>('NHL')

  // Column-specific rosters for both types
  const [leftAhlRoster, setLeftAhlRoster] = useState<PlayerContract[]>([])
  const [leftNhlRoster, setLeftNhlRoster] = useState<PlayerContract[]>([])
  const [rightAhlRoster, setRightAhlRoster] = useState<PlayerContract[]>([])
  const [rightNhlRoster, setRightNhlRoster] = useState<PlayerContract[]>([])

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setCurrentTime(now.toLocaleTimeString('en-US', { 
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      }))
    }
    
    updateTime()
    const interval = setInterval(updateTime, 1000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as HTMLElement
      const insideAny = target.closest('.left-team-dropdown, .right-team-dropdown')
      if (!insideAny) {
        if (isLeftTeamDropdownOpen) setIsLeftTeamDropdownOpen(false)
        if (isRightTeamDropdownOpen) setIsRightTeamDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isLeftTeamDropdownOpen, isRightTeamDropdownOpen])

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch depth chart data to get roster organization
        const depthChartResponse = await getTeamDepthChart(selectedTeam)
        
        if (!depthChartResponse?.success) {
          console.error('Failed to fetch depth chart')
          setLoading(false)
          return
        }
        
        // Get NHL roster (roster_status = 'roster'), AHL roster (roster_status = 'non_roster'), and dead cap/buyout
        const nhlPlayers = depthChartResponse.data.filter(p => p.roster_status === 'roster')
        const ahlPlayers = depthChartResponse.data.filter(p => p.roster_status === 'non_roster')
        const deadCapPlayers = depthChartResponse.data.filter(p => p.dead_cap || p.roster_status === 'dead_cap')
        
        // Contract data is already merged in depthChartResponse.data by the backend
        // No need for additional API calls!
        
        const makeRow = (p: any, roster: 'NHL' | 'AHL') => ({
          playerId: p.player_id?.toString() || '0',
          playerName: p.player_name,
          position: p.position || 'N/A',
          age: p.age || 0,
          capHit: p.cap_hit || 0,
          yearsRemaining: p.years_remaining || 0,
          contractType: p.contract_type || 'Standard',
          rosterStatus: roster,
          deadCap: Boolean(p.dead_cap),
          capHitPercentage: p.cap_percent || 0,
          noTradeClause: false,
          noMovementClause: false,
          baseSalary: 0,
          signingBonus: 0,
          expiryYear: p.expiry_status,
          jerseyNumber: p.jersey_number,
          birthDate: p.birth_date,
          birthCountry: p.birth_country,
          heightInches: p.height_inches,
          weightPounds: p.weight_pounds,
          shootsCatches: p.shoots_catches,
          headshot: p.headshot
        })
        
        // Build combined roster from depth chart (no async calls needed - data already merged)
        const nhlRosterData = nhlPlayers.map(p => makeRow(p, 'NHL'))
        const ahlRosterData = ahlPlayers.map(p => makeRow(p, 'AHL'))
        const deadRosterData = deadCapPlayers.map(p => makeRow(p, 'NHL'))

        // Dedup helper: prefer playerId, fallback to playerName
        const makeKey = (r: PlayerContract) => (r.playerId && r.playerId !== '0') ? `id:${r.playerId}` : `name:${(r.playerName || '').toLowerCase()}`
        const pushUnique = (base: PlayerContract[], extra: PlayerContract[]) => {
          const seen = new Set(base.map(makeKey))
          for (const row of extra) {
            const k = makeKey(row)
            if (!seen.has(k)) { base.push(row); seen.add(k) }
          }
        }

        // Include dead-cap/buyout rows only for NHL view (not AHL)
        pushUnique(nhlRosterData, deadRosterData)
        
        setContracts([...nhlRosterData, ...ahlRosterData])
        setLastUpdated(new Date())
      } catch (error) {
        console.error('Failed to fetch roster data:', error)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
  }, [selectedTeam])

  // Separate contracts by roster status for the "main" selected team (center charts, ticker)
  const nhlRoster = useMemo(() => 
    contracts.filter(c => c.rosterStatus === 'NHL'),
    [contracts]
  )
  
  const ahlRoster = useMemo(() => 
    contracts.filter(c => c.rosterStatus === 'AHL'),
    [contracts]
  )

  const capCeiling = 95500000
  const totalCapHit = useMemo(() => 
    nhlRoster.reduce((sum, c) => sum + c.capHit, 0),
    [nhlRoster]
  )
  const capSpace = capCeiling - totalCapHit

  // Ticker items from contracts
  const tickerItems = useMemo(() => 
    contracts.slice(0, 20).map(c => ({
      playerName: c.playerName,
      capHit: c.capHit,
      status: (c.capHit > 5000000 ? 'overperforming' : c.capHit < 1000000 ? 'underperforming' : 'fair') as 'overperforming' | 'fair' | 'underperforming',
      position: c.position,
      yearsRemaining: c.yearsRemaining,
    })),
    [contracts]
  )

  // Helper to fetch and merge depth chart + contracts for a team
  const fetchRosterContracts = async (team: string) => {
    const depthChartResponse = await getTeamDepthChart(team)
    if (!depthChartResponse?.success) {
      return { nhlRosterData: [] as PlayerContract[], ahlRosterData: [] as PlayerContract[] }
    }

    const nhlPlayers = depthChartResponse.data.filter(p => p.roster_status === 'roster')
    const ahlPlayers = depthChartResponse.data.filter(p => p.roster_status === 'non_roster')
    const deadCapPlayers = depthChartResponse.data.filter(p => p.dead_cap || p.roster_status === 'dead_cap')

    const contractsResponse = await getTeamContracts(team, '2025-2026')
    const contractMap = new Map<string, any>()
    const nameMap = new Map<string, any>()
    const normalizeName = (name: string | undefined | null) =>
      (name || '')
        .normalize('NFD')
        .replace(/\p{Diacritic}/gu, '')
        .toLowerCase()
        .replace(/[^a-z\s'-]/g, '')
        .replace(/\s+/g, ' ')
        .trim()
    if (contractsResponse?.success && contractsResponse.data?.contracts) {
      contractsResponse.data.contracts.forEach((c: any) => {
        const playerId = c.nhl_player_id?.toString()
        if (playerId) contractMap.set(playerId, c)
        const names = [c.full_name, c.player_name]
        names.forEach(n => {
          const key = normalizeName(n)
          if (key) nameMap.set(key, c)
        })
      })
    }

    let nameFallbacks = 0
    const ENABLE_NAME_FALLBACK = (process.env.NEXT_PUBLIC_ENABLE_CONTRACT_NAME_FALLBACK || '').toLowerCase() === 'true'
    const MAX_NAME_FALLBACKS_PER_TEAM = ENABLE_NAME_FALLBACK ? Number(process.env.NEXT_PUBLIC_MAX_NAME_FALLBACKS ?? '0') : 0
    const resolveContract = async (p: DepthChartPlayer) => {
      const pid = p.player_id?.toString()
      if (pid && contractMap.has(pid)) return contractMap.get(pid)
      // Try by player ID via CSV/market API as a robust fallback
      if (pid) {
        try {
          const resp = await getPlayerContract(Number(pid), '2025-2026')
          if (resp?.success && resp.data) return resp.data
        } catch {}
      }
      const nk = normalizeName(p.player_name)
      if (nk && nameMap.has(nk)) return nameMap.get(nk)
      if (nameFallbacks >= MAX_NAME_FALLBACKS_PER_TEAM) return null
      try {
        const resp = await getPlayerContractByName(p.player_name, team, '2025-2026')
        if (resp?.success && resp.data) return resp.data
      } catch {}
      finally { nameFallbacks += 1 }
      return null
    }

    const makeRow = (p: DepthChartPlayer, roster: 'NHL' | 'AHL', contract: any): PlayerContract => ({
      playerId: p.player_id?.toString() || '0',
      playerName: p.player_name,
      position: p.position || 'N/A',
      age: p.age || 0,
      capHit: contract?.cap_hit || 0,
      yearsRemaining: contract?.years_remaining || 0,
      contractType: contract?.contract_type || 'Standard',
      rosterStatus: roster,
      contractStatus: contract?.contract_status,
      deadCap: Boolean(p.dead_cap) || (typeof contract?.contract_status === 'string' && ['buyout','retained','dead_cap','buried'].includes(contract.contract_status.toLowerCase?.() || '')),
      capHitPercentage: contract?.cap_hit_percentage || 0,
      noTradeClause: contract?.no_trade_clause || false,
      noMovementClause: contract?.no_movement_clause || false,
      baseSalary: contract?.base_salary || 0,
      signingBonus: contract?.signing_bonus || 0,
      jerseyNumber: p.jersey_number,
      birthDate: p.birth_date,
      birthCountry: p.birth_country,
      heightInches: p.height_inches,
      weightPounds: p.weight_pounds,
      shootsCatches: p.shoots_catches,
      headshot: p.headshot,
    })

    const nhlRosterData = await Promise.all(nhlPlayers.map(async p => makeRow(p, 'NHL', await resolveContract(p))))
    const ahlRosterData = await Promise.all(ahlPlayers.map(async p => makeRow(p, 'AHL', await resolveContract(p))))
    const deadRosterData = await Promise.all(deadCapPlayers.map(async p => makeRow(p, 'NHL', await resolveContract(p))))

    const makeKey = (r: PlayerContract) => (r.playerId && r.playerId !== '0') ? `id:${r.playerId}` : `name:${(r.playerName || '').toLowerCase()}`
    const pushUnique = (base: PlayerContract[], extra: PlayerContract[]) => {
      const seen = new Set(base.map(makeKey))
      for (const row of extra) {
        const k = makeKey(row)
        if (!seen.has(k)) { base.push(row); seen.add(k) }
      }
    }

    // Include dead-cap/buyout rows only for NHL view (not AHL)
    pushUnique(nhlRosterData, deadRosterData)
    return { nhlRosterData, ahlRosterData }
  }

  // Fetch column-specific rosters on independent selections
  useEffect(() => {
    (async () => {
      try {
        const { nhlRosterData, ahlRosterData } = await fetchRosterContracts(leftTeam)
        setLeftNhlRoster(nhlRosterData)
        setLeftAhlRoster(ahlRosterData)
      } catch (e) {
        console.error('Failed to fetch left team roster', e)
        setLeftNhlRoster([])
        setLeftAhlRoster([])
      }
    })()
  }, [leftTeam])

  useEffect(() => {
    (async () => {
      try {
        const { nhlRosterData, ahlRosterData } = await fetchRosterContracts(rightTeam)
        setRightNhlRoster(nhlRosterData)
        setRightAhlRoster(ahlRosterData)
      } catch (e) {
        console.error('Failed to fetch right team roster', e)
        setRightNhlRoster([])
        setRightAhlRoster([])
      }
    })()
  }, [rightTeam])

  const formatCurrency = (amount: number): string => {
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(2)}M`
    }
    return `$${(amount / 1000).toFixed(0)}K`
  }

  return (
    <BasePage loadingMessage="INITIALIZING CONTRACT TERMINAL...">
      <div className="min-h-screen bg-gray-50 relative flex flex-col dark:bg-gray-950">
        {/* Background grid */}
        <div className="fixed inset-0 opacity-30 pointer-events-none dark:opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(156, 163, 175, 0.15) 1px, transparent 1px),
              linear-gradient(90deg, rgba(156, 163, 175, 0.15) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>
        
        {/* Dark mode grid overlay */}
        <div className="fixed inset-0 opacity-0 pointer-events-none dark:opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>

        {/* Radial gradient overlay */}
        <div className="fixed inset-0 bg-gradient-radial from-red-500/5 via-transparent to-transparent opacity-20 pointer-events-none dark:from-cyan-500/5 dark:opacity-30" />

        {/* Pulse animation intentionally only on Analytics page */}

        {/* Main Container */}
        <div className="relative z-10 flex-1 flex flex-col">
          
          {/* Standard HeartBeat Header */}
          <div className="flex-shrink-0 pt-4 pb-2">
            <div className="mb-2 py-2 flex items-center relative">
              {/* Left: Team Branding with Dropdown - Extreme Left */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center space-x-4 pl-6 z-10"
              >
                <div className="relative">
                  <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse" />
                  <div className="absolute inset-0 w-2 h-2 bg-red-600 rounded-full animate-ping" />
                </div>
                <div>
                  <h2 className="text-xl font-military-display text-gray-900 tracking-wider dark:text-white">
                    {NHL_TEAMS.find(t => t.abbrev === selectedTeam)?.name || 'MONTREAL CANADIENS'}
                  </h2>
                </div>
                <span className="text-xs font-military-display text-gray-500 dark:text-gray-400">2025-2026</span>
              </motion.div>

              {/* Center: HeartBeat Logo */}
              <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="absolute left-[46%] transform -translate-x-1/2 z-0"
              >
                <h1 className="text-2xl font-military-display text-gray-900 tracking-wider dark:text-white">
                  HEARTBEAT
                </h1>
              </motion.div>

              {/* Right: System Info */}
              <motion.div
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                className="ml-auto flex items-center space-x-6 text-gray-500 text-xs font-military-display mr-44 z-10 dark:text-gray-400"
              >
                <div className="flex items-center space-x-2">
                  <ClockIcon className="w-3 h-3 text-gray-900 dark:text-white" />
                  <span className="text-gray-900 dark:text-white">{currentTime}</span>
                </div>
                <span className="text-gray-400 dark:text-gray-500">|</span>
                {lastUpdated && (
                  <span className="text-xs">
                    SYNC {lastUpdated.toLocaleTimeString('en-US', { hour12: false })}
                  </span>
                )}
              </motion.div>
            </div>
          </div>

          {/* Contract Ticker */}
          <div className="flex-shrink-0">
            <ContractTicker items={tickerItems} />
          </div>

          {/* Main Terminal Layout: 3-column grid */}
          <div className="grid grid-cols-[380px_1fr_380px] gap-0 min-h-[800px] pb-12">
            
            {/* LEFT COLUMN: AHL/Minors Roster (independent team selector) */}
            <div className="border-r border-gray-200 bg-white/80 flex flex-col dark:border-white/5 dark:bg-black/20">
              <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 bg-white/90 dark:border-white/5 dark:bg-black/40">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
                      {leftTitleName}
                    </h3>
                    <span className="text-[10px] font-military-display text-gray-600 dark:text-gray-500">
                      ({(leftRosterType === 'NHL' ? leftNhlRoster : leftAhlRoster).length})
                    </span>
                  </div>
                  <div className="relative left-team-dropdown">
                    <button
                      onClick={() => setIsLeftTeamDropdownOpen(!isLeftTeamDropdownOpen)}
                      className="text-[10px] font-military-display text-gray-700 hover:text-gray-900 flex items-center space-x-1 px-2 py-1 border border-gray-300 rounded dark:text-gray-300 dark:hover:text-white dark:border-white/10"
                    >
                      <span>{leftTeam}</span>
                      <ChevronDownIcon className={`w-3 h-3 ${isLeftTeamDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {isLeftTeamDropdownOpen && (
                      <div className="absolute right-0 mt-2 w-56 bg-white/95 border border-gray-200 rounded shadow-xl z-50 backdrop-blur-sm dark:bg-black/95 dark:border-white/20">
                        <div className="max-h-72 overflow-y-auto custom-scrollbar">
                          <div className="border-b border-gray-200 dark:border-white/10">
                            <div className="px-3 py-1 bg-gray-100 border-b border-gray-200 dark:bg-black/60 dark:border-white/10">
                              <span className="text-[10px] font-military-display text-gray-600 tracking-widest dark:text-gray-400">SELECTED</span>
                            </div>
                            {(() => {
                              const t = getTeamInfo(leftTeam)
                              if (!t) return null
                              return (
                                <>
                                  <button
                                    onClick={() => { setLeftTeam(t.abbrev); setLeftTitleName(t.name); setLeftRosterType('NHL'); setIsLeftTeamDropdownOpen(false) }}
                                    className={`w-full px-3 py-1.5 text-left text-xs font-military-display hover:bg-gray-100 transition-colors ${leftTitleName === t.name ? 'bg-gray-200 text-gray-900' : 'text-gray-700'} dark:hover:bg-white/10 ${leftTitleName === t.name ? 'dark:bg-white/20 dark:text-white' : 'dark:text-gray-300'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{t.name}</span>
                                      <span className="text-[10px] text-gray-500">{t.abbrev}</span>
                                    </div>
                                  </button>
                                  <button
                                    onClick={() => { setLeftTeam(t.abbrev); setLeftTitleName(t.ahl); setLeftRosterType('AHL'); setIsLeftTeamDropdownOpen(false) }}
                                    className={`w-full pl-6 pr-3 py-1 text-left text-[11px] font-military-display hover:bg-gray-100 transition-colors ${leftTitleName === t.ahl ? 'bg-gray-100 text-gray-800' : 'text-gray-600'} dark:hover:bg-white/10 ${leftTitleName === t.ahl ? 'dark:bg-white/10 dark:text-gray-200' : 'dark:text-gray-400'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{t.ahl}</span>
                                      <span className="text-[10px] text-gray-500">{t.abbrev}</span>
                                    </div>
                                  </button>
                                </>
                              )
                            })()}
                          </div>
                          {['Atlantic', 'Metropolitan', 'Central', 'Pacific'].map(division => (
                            <div key={division} className="border-b border-gray-200 last:border-b-0 dark:border-white/5">
                              <div className="px-3 py-1 bg-gray-100 border-b border-gray-200 dark:bg-black/60 dark:border-white/10">
                                <span className="text-[10px] font-military-display text-gray-600 tracking-widest dark:text-gray-400">
                                  {division.toUpperCase()} DIVISION
                                </span>
                              </div>
                              {NHL_TEAMS.filter(t => t.division === division).map(team => (
                                <div key={team.abbrev} className="border-b border-gray-200 last:border-b-0 dark:border-white/5">
                                   <button
                                    onClick={() => { setLeftTeam(team.abbrev); setLeftTitleName(team.name); setLeftRosterType('NHL'); setIsLeftTeamDropdownOpen(false) }}
                                    className={`w-full px-3 py-1.5 text-left text-xs font-military-display hover:bg-gray-100 transition-colors ${leftTeam === team.abbrev ? 'bg-gray-200 text-gray-900' : 'text-gray-700'} dark:hover:bg-white/10 ${leftTeam === team.abbrev ? 'dark:bg-white/20 dark:text-white' : 'dark:text-gray-300'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{team.name}</span>
                                      <span className="text-[10px] text-gray-500">{team.abbrev}</span>
                                    </div>
                                  </button>
                                  <button
                                    onClick={() => { setLeftTeam(team.abbrev); setLeftTitleName(team.ahl); setLeftRosterType('AHL'); setIsLeftTeamDropdownOpen(false) }}
                                    className={`w-full pl-6 pr-3 py-1 text-left text-[11px] font-military-display hover:bg-gray-100 transition-colors ${leftTeam === team.abbrev ? 'bg-gray-100 text-gray-800' : 'text-gray-600'} dark:hover:bg-white/10 ${leftTeam === team.abbrev ? 'dark:bg-white/10 dark:text-gray-200' : 'dark:text-gray-400'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{team.ahl}</span>
                                      <span className="text-[10px] text-gray-500">{team.abbrev}</span>
                                    </div>
                                  </button>
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                <RosterContractList contracts={leftRosterType === 'NHL' ? leftNhlRoster : leftAhlRoster} compact />
              </div>
            </div>

            {/* CENTER COLUMN: Main Terminal Display */}
            <div className="flex flex-col">
              {/* Contract Analytics Visualization */}
              <div className="p-6">
                <ContractTimeline 
                  contracts={nhlRoster} 
                  capCeiling={capCeiling}
                  totalCapHit={totalCapHit}
                />
              </div>

              {/* Bottom Section: Activity Feed */}
              <div className="px-6 pb-6 pt-4 border-t border-gray-200 min-h-[280px] dark:border-white/5">
                <ActivityFeed teamAbbrev={selectedTeam} />
              </div>
            </div>

            {/* RIGHT COLUMN: NHL Roster (independent team selector) */}
            <div className="border-l border-gray-200 bg-white/80 flex flex-col dark:border-white/5 dark:bg-black/20">
              <div className="flex-shrink-0 px-4 py-3 border-b border-gray-200 bg-white/90 dark:border-white/5 dark:bg-black/40">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <h3 className="text-xs font-military-display text-gray-900 uppercase tracking-widest dark:text-white">
                      {rightTitleName}
                    </h3>
                    <span className="text-[10px] font-military-display text-gray-600 dark:text-gray-500">
                      ({(rightRosterType === 'NHL' ? rightNhlRoster : rightAhlRoster).length})
                    </span>
                  </div>
                  <div className="relative right-team-dropdown">
                    <button
                      onClick={() => setIsRightTeamDropdownOpen(!isRightTeamDropdownOpen)}
                      className="text-[10px] font-military-display text-gray-700 hover:text-gray-900 flex items-center space-x-1 px-2 py-1 border border-gray-300 rounded dark:text-gray-300 dark:hover:text-white dark:border-white/10"
                    >
                      <span>{rightTeam}</span>
                      <ChevronDownIcon className={`w-3 h-3 ${isRightTeamDropdownOpen ? 'rotate-180' : ''}`} />
                    </button>
                    {isRightTeamDropdownOpen && (
                      <div className="absolute right-0 mt-2 w-56 bg-white/95 border border-gray-200 rounded shadow-xl z-50 backdrop-blur-sm dark:bg-black/95 dark:border-white/20">
                        <div className="max-h-72 overflow-y-auto custom-scrollbar">
                          <div className="border-b border-gray-200 dark:border-white/10">
                            <div className="px-3 py-1 bg-gray-100 border-b border-gray-200 dark:bg-black/60 dark:border-white/10">
                              <span className="text-[10px] font-military-display text-gray-600 tracking-widest dark:text-gray-400">SELECTED</span>
                            </div>
                            {(() => {
                              const t = getTeamInfo(rightTeam)
                              if (!t) return null
                              return (
                                <>
                                  <button
                                    onClick={() => { setRightTeam(t.abbrev); setRightTitleName(t.name); setRightRosterType('NHL'); setIsRightTeamDropdownOpen(false) }}
                                    className={`w-full px-3 py-1.5 text-left text-xs font-military-display hover:bg-gray-100 transition-colors ${rightTitleName === t.name ? 'bg-gray-200 text-gray-900' : 'text-gray-700'} dark:hover:bg-white/10 ${rightTitleName === t.name ? 'dark:bg-white/20 dark:text-white' : 'dark:text-gray-300'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{t.name}</span>
                                      <span className="text-[10px] text-gray-500">{t.abbrev}</span>
                                    </div>
                                  </button>
                                  <button
                                    onClick={() => { setRightTeam(t.abbrev); setRightTitleName(t.ahl); setRightRosterType('AHL'); setIsRightTeamDropdownOpen(false) }}
                                    className={`w-full pl-6 pr-3 py-1 text-left text-[11px] font-military-display hover:bg-gray-100 transition-colors ${rightTitleName === t.ahl ? 'bg-gray-100 text-gray-800' : 'text-gray-600'} dark:hover:bg-white/10 ${rightTitleName === t.ahl ? 'dark:bg-white/10 dark:text-gray-200' : 'dark:text-gray-400'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{t.ahl}</span>
                                      <span className="text-[10px] text-gray-500">{t.abbrev}</span>
                                    </div>
                                  </button>
                                </>
                              )
                            })()}
                          </div>
                          {['Atlantic', 'Metropolitan', 'Central', 'Pacific'].map(division => (
                            <div key={division} className="border-b border-gray-200 last:border-b-0 dark:border-white/5">
                              <div className="px-3 py-1 bg-gray-100 border-b border-gray-200 dark:bg-black/60 dark:border-white/10">
                                <span className="text-[10px] font-military-display text-gray-600 tracking-widest dark:text-gray-400">
                                  {division.toUpperCase()} DIVISION
                                </span>
                              </div>
                              {NHL_TEAMS.filter(t => t.division === division).map(team => (
                                <div key={team.abbrev} className="border-b border-gray-200 last:border-b-0 dark:border-white/5">
                                  <button
                                    onClick={() => { setRightTeam(team.abbrev); setRightTitleName(team.name); setRightRosterType('NHL'); setIsRightTeamDropdownOpen(false) }}
                                    className={`w-full px-3 py-1.5 text-left text-xs font-military-display hover:bg-gray-100 transition-colors ${rightTeam === team.abbrev ? 'bg-gray-200 text-gray-900' : 'text-gray-700'} dark:hover:bg-white/10 ${rightTeam === team.abbrev ? 'dark:bg-white/20 dark:text-white' : 'dark:text-gray-300'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{team.name}</span>
                                      <span className="text-[10px] text-gray-500">{team.abbrev}</span>
                                    </div>
                                  </button>
                                  <button
                                    onClick={() => { setRightTeam(team.abbrev); setRightTitleName(team.ahl); setRightRosterType('AHL'); setIsRightTeamDropdownOpen(false) }}
                                    className={`w-full pl-6 pr-3 py-1 text-left text-[11px] font-military-display hover:bg-gray-100 transition-colors ${rightTeam === team.abbrev ? 'bg-gray-100 text-gray-800' : 'text-gray-600'} dark:hover:bg-white/10 ${rightTeam === team.abbrev ? 'dark:bg-white/10 dark:text-gray-200' : 'dark:text-gray-400'}`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span>{team.ahl}</span>
                                      <span className="text-[10px] text-gray-500">{team.abbrev}</span>
                                    </div>
                                  </button>
                                </div>
                              ))}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              <div className="flex-1 overflow-y-auto">
                <RosterContractList contracts={rightRosterType === 'NHL' ? rightNhlRoster : rightAhlRoster} compact />
              </div>
            </div>

          </div>
        </div>
      </div>
    </BasePage>
  )
}
