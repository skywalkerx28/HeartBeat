'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CpuChipIcon, BoltIcon, CursorArrowRaysIcon } from '@heroicons/react/24/outline'

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

interface PulseAdvancedPredictionProps {
  predictions: Prediction[]
  gameData: any
}

export function PulseAdvancedPrediction({ predictions, gameData }: PulseAdvancedPredictionProps) {
  const [selectedPrediction, setSelectedPrediction] = useState<string | null>(null)
  const [animatingBars, setAnimatingBars] = useState(true)

  useEffect(() => {
    const interval = setInterval(() => {
      setAnimatingBars(prev => !prev)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  const topPrediction = predictions[0]

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900/80 border border-red-600/30 rounded-lg p-4 backdrop-blur-sm"
    >
      {/* Header */}
      <div className="flex items-center space-x-3 mb-6">
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
            ADVANCED PREDICTION MATRIX
          </h3>
          <p className="text-sm font-military-display text-gray-400">
            NEURAL LINE MATCHUP ANALYSIS
          </p>
        </div>
      </div>

      {/* Top Prediction Highlight */}
      {topPrediction && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="mb-6 p-4 bg-red-600/10 border border-red-600/50 rounded-lg"
        >
          <div className="flex items-center space-x-2 mb-3">
            <CursorArrowRaysIcon className="w-5 h-5 text-red-400" />
            <span className="text-sm font-military-display text-red-400 tracking-wider">
              PRIMARY PREDICTION
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-3">
            <div>
              <div className="text-xs font-military-display text-gray-500 mb-1">FORWARDS</div>
              <div className="text-lg font-military-chat text-white">
                {topPrediction.forwardsNames.join(' • ')}
              </div>
            </div>
            <div>
              <div className="text-xs font-military-display text-gray-500 mb-1">DEFENSE</div>
              <div className="text-lg font-military-chat text-white">
                {topPrediction.defenseNames.join(' • ')}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            <div className="flex-1">
              <div className="flex justify-between text-xs font-military-display text-gray-400 mb-1">
                <span>PROBABILITY</span>
                <span>{(topPrediction.probability * 100).toFixed(1)}%</span>
              </div>
              <div className="w-full bg-gray-800 rounded-full h-3">
                <motion.div
                  className="bg-red-600 h-3 rounded-full"
                  initial={{ width: 0 }}
                  animate={{ width: `${topPrediction.probability * 100}%` }}
                  transition={{ duration: 1.5, ease: "easeOut" }}
                />
              </div>
            </div>

            <div className="text-right">
              <div className="text-2xl font-military-display font-bold text-red-400">
                {(topPrediction.probability * 100).toFixed(1)}%
              </div>
              <div className="text-xs font-military-display text-gray-500">
                CONFIDENCE
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {/* Probability Matrix */}
      <div className="mb-6">
        <div className="text-sm font-military-display text-gray-400 mb-3 tracking-wider">
          PREDICTION MATRIX
        </div>

        <div className="space-y-2">
          {predictions.map((prediction, index) => (
            <motion.div
              key={prediction.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className={`
                relative p-3 rounded border cursor-pointer transition-all
                ${selectedPrediction === prediction.id
                  ? 'border-red-600/70 bg-red-600/10'
                  : 'border-gray-700/50 bg-gray-800/30 hover:border-gray-600/70'
                }
              `}
              onClick={() => setSelectedPrediction(
                selectedPrediction === prediction.id ? null : prediction.id
              )}
            >
              {/* Animated background for top prediction */}
              {index === 0 && (
                <motion.div
                  animate={{
                    background: [
                      'linear-gradient(90deg, transparent 0%, rgba(239, 68, 68, 0.1) 50%, transparent 100%)',
                      'linear-gradient(90deg, transparent 100%, rgba(239, 68, 68, 0.1) 50%, transparent 0%)'
                    ]
                  }}
                  transition={{ duration: 3, repeat: Infinity }}
                  className="absolute inset-0 rounded"
                />
              )}

              <div className="relative z-10 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`
                    w-6 h-6 rounded-full flex items-center justify-center text-xs font-military-display
                    ${index === 0 ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-300'}
                  `}>
                    {index + 1}
                  </div>

                  <div>
                    <div className="text-sm font-military-chat text-white">
                      {prediction.forwardsNames.slice(0, 2).join(' • ')}
                      {prediction.forwardsNames.length > 2 && '...'}
                    </div>
                    <div className="text-xs font-military-display text-gray-500">
                      {prediction.defenseNames.join(' • ')}
                    </div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-lg font-military-display font-bold text-white">
                    {(prediction.probability * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs font-military-display text-gray-500">
                    {(prediction.confidence * 100).toFixed(0)}% conf
                  </div>
                </div>
              </div>

              {/* Expandable details */}
              <AnimatePresence>
                {selectedPrediction === prediction.id && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="mt-3 pt-3 border-t border-gray-700"
                  >
                    <div className="text-xs font-military-display text-gray-400 leading-relaxed">
                      {prediction.explanation}
                    </div>

                    {/* Confidence meter */}
                    <div className="mt-3">
                      <div className="flex justify-between text-xs font-military-display text-gray-500 mb-1">
                        <span>CONFIDENCE LEVEL</span>
                        <span>{(prediction.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <div className="w-full bg-gray-800 rounded-full h-2">
                        <motion.div
                          className={`h-2 rounded-full ${
                            prediction.confidence >= 0.8 ? 'bg-red-600' :
                            prediction.confidence >= 0.6 ? 'bg-gray-400' : 'bg-gray-600'
                          }`}
                          initial={{ width: 0 }}
                          animate={{ width: `${prediction.confidence * 100}%` }}
                          transition={{ duration: 0.8 }}
                        />
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Neural Network Status */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-700">
        <div className="flex items-center space-x-3">
          <motion.div
            animate={{ rotate: animatingBars ? 360 : 0 }}
            transition={{ duration: 2, ease: "linear" }}
            className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full"
          />
          <span className="text-sm font-military-display text-red-400">
            NEURAL ENGINE ACTIVE
          </span>
        </div>

        <div className="flex items-center space-x-2">
          <BoltIcon className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-military-display text-gray-400">
            REAL-TIME PROCESSING
          </span>
        </div>
      </div>
    </motion.div>
  )
}
