'use client'

import { motion } from 'framer-motion'
import { CpuChipIcon, BoltIcon, ExclamationTriangleIcon } from '@heroicons/react/24/outline'

interface Prediction {
  id: string
  probability: number
  confidence: number
  forwards: string[]
  forwardsNames: string[]
  defense: string[]
  defenseNames: string[]
  explanation: string
}

interface GameData {
  zone: string
  strength: string
  score_differential?: number
  period: number
  periodTime: number
}

interface PulsePredictionEngineProps {
  predictions: Prediction[]
  gameData: GameData
}

export function PulsePredictionEngine({ predictions, gameData }: PulsePredictionEngineProps) {
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-red-400 border-red-600/50 bg-red-600/10'
    if (confidence >= 0.6) return 'text-gray-400 border-gray-600/50 bg-gray-600/10'
    return 'text-gray-500 border-gray-600/50 bg-gray-600/10'
  }

  const getConfidenceIcon = (confidence: number) => {
    if (confidence >= 0.8) return BoltIcon
    if (confidence >= 0.6) return ExclamationTriangleIcon
    return ExclamationTriangleIcon
  }

  const formatLine = (players: string[]) => {
    return players.join(' - ')
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900/80 border border-red-600/30 rounded-lg p-4 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center space-x-3 mb-4">
        <CpuChipIcon className="w-5 h-5 text-red-400" />
        <div>
          <h3 className="text-lg font-military-display text-white">
            PREDICTION ENGINE
          </h3>
          <p className="text-xs font-military-display text-gray-400">
            LINE MATCHUP ANALYSIS
          </p>
        </div>
      </div>

      {/* Current Game Context */}
      <div className="mb-4 p-3 bg-gray-800/50 border border-gray-700 rounded-lg">
        <div className="text-xs font-military-display text-gray-500 mb-2 tracking-wider">
          CURRENT SITUATION
        </div>
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-gray-300">
            <span className="text-red-400">ZONE:</span> {gameData.zone.toUpperCase()}
          </div>
          <div className="text-gray-300">
            <span className="text-gray-400">STRENGTH:</span> {gameData.strength}
          </div>
        </div>
      </div>

      {/* Predictions List */}
      <div className="space-y-3">
        {predictions.map((prediction, index) => {
          const ConfidenceIcon = getConfidenceIcon(prediction.confidence)
          const isTopPrediction = index === 0

          return (
            <motion.div
              key={prediction.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`
                border rounded-lg p-3 transition-all
                ${isTopPrediction
                  ? 'border-red-600/50 bg-red-600/5 shadow-lg shadow-red-600/20'
                  : 'border-gray-700/50 bg-gray-800/30 hover:border-gray-600/70'
                }
              `}
            >
              {/* Prediction Header */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-2">
                  {isTopPrediction && (
                    <motion.div
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="w-2 h-2 bg-red-500 rounded-full"
                    />
                  )}
                  <span className="text-sm font-military-display text-gray-400">
                    PREDICTION #{index + 1}
                  </span>
                </div>

                <div className={`flex items-center space-x-1 px-2 py-1 rounded text-xs font-military-display ${getConfidenceColor(prediction.confidence)}`}>
                  <ConfidenceIcon className="w-3 h-3" />
                  <span>{(prediction.confidence * 100).toFixed(0)}%</span>
                </div>
              </div>

              {/* Probability Bar */}
              <div className="mb-3">
                <div className="flex justify-between text-xs font-military-display text-gray-400 mb-1">
                  <span>PROBABILITY</span>
                  <span>{(prediction.probability * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-800 rounded-full h-2">
                  <motion.div
                    className={`h-2 rounded-full ${isTopPrediction ? 'bg-red-600' : 'bg-gray-600'}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${prediction.probability * 100}%` }}
                    transition={{ duration: 1, delay: index * 0.1 }}
                  />
                </div>
              </div>

              {/* Line Composition */}
              <div className="space-y-2 mb-3">
                <div>
                  <div className="text-xs font-military-display text-gray-500 tracking-wider mb-1">
                    FORWARDS
                  </div>
                  <div className="text-sm font-military-chat text-white">
                    {formatLine(prediction.forwardsNames)}
                  </div>
                </div>

                <div>
                  <div className="text-xs font-military-display text-gray-500 tracking-wider mb-1">
                    DEFENSE PAIR
                  </div>
                  <div className="text-sm font-military-chat text-white">
                    {formatLine(prediction.defenseNames)}
                  </div>
                </div>
              </div>

              {/* Explanation */}
              <div className="text-xs font-military-display text-gray-400 leading-relaxed">
                {prediction.explanation}
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Engine Status */}
      <div className="mt-4 pt-3 border-t border-gray-700">
        <div className="flex items-center justify-center space-x-2">
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
            className="w-3 h-3 border border-red-600 border-t-transparent rounded-full"
          />
          <span className="text-xs font-military-display text-red-400 tracking-wider">
            NEURAL NETWORK ACTIVE
          </span>
        </div>
      </div>
    </motion.div>
  )
}
