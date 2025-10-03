'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CpuChipIcon, ShieldCheckIcon, ExclamationTriangleIcon, ArrowTrendingUpIcon } from '@heroicons/react/24/outline'

interface StrategicAnalysis {
  scenario: string
  strategicAdvantage: string
  confidence: number
  inferenceTimeMs: number
  mtlDeploymentOptions: Array<{
    players: string[]
    playersNames: string[]
    probabilityPrior: number
    matchupPrior: number
    chemistryScore: number
    fatigueScore: number
    riskLevel: string
  }>
  riskAnalysis: Array<{
    mtlDeployment: string[]
    mtlNames: string[]
    opponentCounterResponses: Array<{
      players: string[]
      playersNames: string[]
      probability: number
      threatLevel: number
      matchupQuality: number
    }>
  }>
  strategicRecommendation: {
    mtlDeployment: string[]
    mtlNames: string[]
    expectedValue: number
    riskLevel: string
    reasoning: string
  }
}

interface GameData {
  decisionRole: number
  hasLastChange: boolean
  lastStoppageType: string
  lastStoppageDuration: number
  lastStoppageTime: string
}

interface PulseStrategicAnalysisProps {
  strategicAnalysis: StrategicAnalysis
  gameData: GameData
}

export function PulseStrategicAnalysis({ strategicAnalysis, gameData }: PulseStrategicAnalysisProps) {
  const [expandedView, setExpandedView] = useState(false)

  const getAdvantageColor = (advantage: string) => {
    switch (advantage) {
      case 'MTL': return 'text-red-400 bg-red-600/10 border-red-600/30'
      case 'OPPONENT': return 'text-gray-400 bg-gray-600/10 border-gray-600/30'
      default: return 'text-yellow-400 bg-yellow-600/10 border-yellow-600/30'
    }
  }

  const getRiskColor = (riskLevel: string) => {
    switch (riskLevel) {
      case 'LOW': return 'text-green-400 bg-green-600/10'
      case 'MEDIUM': return 'text-yellow-400 bg-yellow-600/10'
      case 'HIGH': return 'text-red-400 bg-red-600/10'
      default: return 'text-gray-400 bg-gray-600/10'
    }
  }

  const getThreatColor = (threatLevel: number) => {
    if (threatLevel >= 0.7) return 'text-red-400'
    if (threatLevel >= 0.4) return 'text-yellow-400'
    return 'text-green-400'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900/80 border border-red-600/30 rounded-lg p-4 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className="relative">
            <CpuChipIcon className="w-6 h-6 text-red-400" />
            <motion.div
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
              className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full"
            />
          </div>
          <div>
            <h3 className="text-xl font-military-display text-white">
              STRATEGIC ANALYSIS MATRIX
            </h3>
            <p className="text-sm font-military-display text-gray-400">
              BIDIRECTIONAL PREDICTION ENGINE
            </p>
          </div>
        </div>

        <button
          onClick={() => setExpandedView(!expandedView)}
          className="text-xs font-military-display text-gray-400 hover:text-white transition-colors"
        >
          {expandedView ? 'COLLAPSE' : 'EXPAND'}
        </button>
      </div>

      {/* Strategic Advantage */}
      <div className="mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldCheckIcon className="w-5 h-5 text-gray-400" />
            <span className="text-sm font-military-display text-gray-400 tracking-wider">
              STRATEGIC ADVANTAGE
            </span>
          </div>
          <div className={`px-3 py-1 rounded border text-sm font-military-display ${getAdvantageColor(strategicAnalysis.strategicAdvantage)}`}>
            {strategicAnalysis.strategicAdvantage}
          </div>
        </div>
        <div className="mt-2 text-xs font-military-display text-gray-500">
          {strategicAnalysis.scenario.replace('_', ' ').toUpperCase()} • {gameData.lastStoppageType?.toUpperCase()} {gameData.lastStoppageTime}
        </div>
      </div>

      {/* Strategic Recommendation */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mb-6 p-4 bg-red-600/10 border border-red-600/50 rounded-lg"
      >
        <div className="flex items-center space-x-2 mb-3">
          <ArrowTrendingUpIcon className="w-5 h-5 text-red-400" />
          <span className="text-sm font-military-display text-red-400 tracking-wider">
            OPTIMAL STRATEGY
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="text-xs font-military-display text-gray-500 mb-1">RECOMMENDED LINEUP</div>
            <div className="text-lg font-military-chat text-white">
              {strategicAnalysis.strategicRecommendation.mtlNames.join(' • ')}
            </div>
          </div>
          <div className="text-right">
            <div className={`inline-block px-2 py-1 rounded text-sm font-military-display ${getRiskColor(strategicAnalysis.strategicRecommendation.riskLevel)}`}>
              {strategicAnalysis.strategicRecommendation.riskLevel} RISK
            </div>
            <div className="text-xs font-military-display text-gray-500 mt-1">
              EV: {(strategicAnalysis.strategicRecommendation.expectedValue * 100).toFixed(1)}%
            </div>
          </div>
        </div>

        <div className="mt-3 text-xs font-military-display text-gray-400 leading-relaxed">
          {strategicAnalysis.strategicRecommendation.reasoning}
        </div>
      </motion.div>

      {/* Deployment Options */}
      <div className="mb-4">
        <div className="text-sm font-military-display text-gray-400 mb-3 tracking-wider">
          DEPLOYMENT OPTIONS
        </div>

        <div className="space-y-2">
          {strategicAnalysis.mtlDeploymentOptions.map((option, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`
                p-3 rounded border cursor-pointer transition-all
                ${index === 0 ? 'border-red-600/50 bg-red-600/5' : 'border-gray-700/50 bg-gray-800/30 hover:border-gray-600/70'}
              `}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`
                    w-6 h-6 rounded-full flex items-center justify-center text-xs font-military-display
                    ${index === 0 ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-300'}
                  `}>
                    {index + 1}
                  </div>
                  <div>
                    <div className="text-sm font-military-chat text-white">
                      {option.playersNames.join(' • ')}
                    </div>
                    <div className="text-xs font-military-display text-gray-500">
                      P: {(option.probabilityPrior * 100).toFixed(1)}% •
                      Matchup: {option.matchupPrior >= 0 ? '+' : ''}{(option.matchupPrior * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>

                <div className={`px-2 py-1 rounded text-xs font-military-display ${getRiskColor(option.riskLevel)}`}>
                  {option.riskLevel}
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Risk Analysis - Expandable */}
      <AnimatePresence>
        {expandedView && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="border-t border-gray-700 pt-4"
          >
            <div className="text-sm font-military-display text-gray-400 mb-3 tracking-wider">
              OPPONENT COUNTER-RESPONSES
            </div>

            {strategicAnalysis.riskAnalysis.map((risk, riskIndex) => (
              <div key={riskIndex} className="mb-4">
                <div className="text-xs font-military-display text-gray-500 mb-2">
                  VS: {risk.mtlNames.join(' • ')}
                </div>

                <div className="space-y-2">
                  {risk.opponentCounterResponses.map((response, respIndex) => (
                    <div key={respIndex} className="p-2 bg-gray-800/50 rounded border border-gray-700">
                      <div className="flex items-center justify-between">
                        <div className="text-sm font-military-chat text-white">
                          {response.playersNames.join(' • ')}
                        </div>
                        <div className="flex items-center space-x-3">
                          <div className="text-xs font-military-display text-gray-400">
                            P: {(response.probability * 100).toFixed(1)}%
                          </div>
                          <div className={`text-xs font-military-display ${getThreatColor(response.threatLevel)}`}>
                            THREAT: {(response.threatLevel * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>
                      <div className="text-xs font-military-display text-gray-500 mt-1">
                        Matchup Quality: {(response.matchupQuality * 100).toFixed(1)}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Performance Metrics */}
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="flex items-center justify-between text-xs font-military-display text-gray-500">
                <span>ANALYSIS TIME</span>
                <span>{strategicAnalysis.inferenceTimeMs.toFixed(1)}ms</span>
              </div>
              <div className="flex items-center justify-between text-xs font-military-display text-gray-500 mt-1">
                <span>CONFIDENCE</span>
                <span>{(strategicAnalysis.confidence * 100).toFixed(1)}%</span>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer Status */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-700">
        <div className="flex items-center space-x-2">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full"
          />
          <span className="text-sm font-military-display text-red-400">
            STRATEGIC ENGINE ACTIVE
          </span>
        </div>

        <div className="text-xs font-military-display text-gray-400">
          DECISION ROLE: {gameData.decisionRole === 1 ? 'ADVANTAGE' : 'REACTION'}
        </div>
      </div>
    </motion.div>
  )
}
