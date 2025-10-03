'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BasePage } from '../../components/layout/BasePage'
import { PulseGameDashboard } from '../../components/pulse/PulseGameDashboard'
import { PulseAdvancedPrediction } from '../../components/pulse/PulseAdvancedPrediction'
import { PulseMetricsStream } from '../../components/pulse/PulseMetricsStream'
import { PulseUnifiedRoster } from '../../components/pulse/PulseUnifiedRoster'
import { PulseStrategicAnalysis } from '../../components/pulse/PulseStrategicAnalysis'
import { PulsePhaseIndicators } from '../../components/pulse/PulsePhaseIndicators'
import { PulseOnIceFormation } from '../../components/pulse/PulseOnIceFormation'
import { PulsePlayerChangeLog } from '../../components/pulse/PulsePlayerChangeLog'

// Mock data for development - will be replaced with real API data
const mockGameData = {
  gameId: "MTL-VS-BOS-2025-01-15",
  homeTeam: "MTL",
  awayTeam: "BOS",
  homeScore: 2,
  awayScore: 1,
  period: 2,
  periodTime: 8.34, // minutes remaining
  gameTime: 41.26, // total game time
  status: "LIVE",
  zone: "NZ",
  strength: "5v5",
  lastEvent: "Faceoff Won",
  lastEventTime: "2:15 ago",
  // ENHANCED GAME STATE FROM BACKEND
  scoreDifferential: -1, // From MTL perspective
  hasLastChange: false, // BOS has last change advantage
  isPeriodLate: false, // Not late in period yet
  isGameLate: false, // Not late in game yet
  isLatePk: false, // No PK situation
  isLatePp: false, // No PP situation
  isCloseAndLate: false, // Not close and late
  lastStoppageType: "icing",
  lastStoppageDuration: 45.2,
  lastStoppageTime: "1:32 ago",
  decisionRole: 0 // Opponent has tactical advantage
}

const mockMtlRoster = {
  onIce: {
    forwards: [
      {
        id: "8480018",
        name: "Cole Caufield",
        position: "RW",
        number: 22,
        // ENHANCED FATIGUE TRACKING FROM BACKEND
        restGameTime: 45.2,
        restRealTime: 52.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 8,
        shiftsTotalGame: 24,
        toiPast20min: 12.3,
        toiCumulativeGame: 18.7,
        ewmaShiftLength: 42.1,
        ewmaRestLength: 88.5,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8479318",
        name: "Kirby Dach",
        position: "C",
        number: 77,
        restGameTime: 28.7,
        restRealTime: 31.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 12,
        shiftsTotalGame: 32,
        toiPast20min: 15.8,
        toiCumulativeGame: 22.4,
        ewmaShiftLength: 38.9,
        ewmaRestLength: 72.3,
        isWellRested: false,
        isOverused: true,
        isHeavyToi: false
      },
      {
        id: "8481540",
        name: "Christian Dvorak",
        position: "C",
        number: 15,
        restGameTime: 62.1,
        restRealTime: 68.9,
        intermissionFlag: 0,
        shiftsThisPeriod: 6,
        shiftsTotalGame: 18,
        toiPast20min: 8.7,
        toiCumulativeGame: 14.2,
        ewmaShiftLength: 45.6,
        ewmaRestLength: 95.8,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    defense: [
      {
        id: "8476875",
        name: "Mike Matheson",
        position: "D",
        number: 8,
        restGameTime: 35.8,
        restRealTime: 39.4,
        intermissionFlag: 0,
        shiftsThisPeriod: 10,
        shiftsTotalGame: 28,
        toiPast20min: 14.6,
        toiCumulativeGame: 21.8,
        ewmaShiftLength: 48.2,
        ewmaRestLength: 78.9,
        isWellRested: false,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8482087",
        name: "Kaiden Guhle",
        position: "D",
        number: 24,
        restGameTime: 52.3,
        restRealTime: 58.7,
        intermissionFlag: 0,
        shiftsThisPeriod: 7,
        shiftsTotalGame: 20,
        toiPast20min: 10.4,
        toiCumulativeGame: 16.9,
        ewmaShiftLength: 41.8,
        ewmaRestLength: 92.1,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    goalie: {
      id: "8474596",
      name: "Jake Allen",
      position: "G",
      number: 34,
      restGameTime: 1200.0, // Goalies don't track shifts like skaters
      restRealTime: 1200.0,
      intermissionFlag: 0,
      shiftsThisPeriod: 0,
      shiftsTotalGame: 0,
      toiPast20min: 0.0,
      toiCumulativeGame: 0.0,
      ewmaShiftLength: 0.0,
      ewmaRestLength: 0.0,
      isWellRested: true,
      isOverused: false,
      isHeavyToi: false
    }
  },
  bench: {
    forwards: [
      {
        id: "8476458",
        name: "Juraj Slafkovsky",
        position: "LW",
        number: 20,
        restGameTime: 180.5,
        restRealTime: 195.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 8,
        toiPast20min: 3.2,
        toiCumulativeGame: 6.8,
        ewmaShiftLength: 39.4,
        ewmaRestLength: 120.5,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477476",
        name: "Josh Anderson",
        position: "RW",
        number: 17,
        restGameTime: 95.8,
        restRealTime: 102.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 4,
        shiftsTotalGame: 12,
        toiPast20min: 6.9,
        toiCumulativeGame: 11.4,
        ewmaShiftLength: 36.7,
        ewmaRestLength: 85.2,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477426",
        name: "Michael Pezzetta",
        position: "LW",
        number: 55,
        restGameTime: 75.4,
        restRealTime: 82.1,
        intermissionFlag: 0,
        shiftsThisPeriod: 5,
        shiftsTotalGame: 15,
        toiPast20min: 8.3,
        toiCumulativeGame: 13.7,
        ewmaShiftLength: 44.2,
        ewmaRestLength: 78.9,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8478131",
        name: "Rafael Harvey-Pinard",
        position: "LW",
        number: 49,
        restGameTime: 210.3,
        restRealTime: 225.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 1,
        shiftsTotalGame: 4,
        toiPast20min: 1.8,
        toiCumulativeGame: 3.9,
        ewmaShiftLength: 35.6,
        ewmaRestLength: 145.2,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477015",
        name: "Connor Barron",
        position: "C",
        number: 82,
        restGameTime: 165.7,
        restRealTime: 178.4,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 7,
        toiPast20min: 2.9,
        toiCumulativeGame: 6.2,
        ewmaShiftLength: 38.1,
        ewmaRestLength: 112.3,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8475191",
        name: "Jesse Ylonen",
        position: "RW",
        number: 71,
        restGameTime: 245.6,
        restRealTime: 258.9,
        intermissionFlag: 0,
        shiftsThisPeriod: 0,
        shiftsTotalGame: 2,
        toiPast20min: 0.7,
        toiCumulativeGame: 2.1,
        ewmaShiftLength: 41.3,
        ewmaRestLength: 180.7,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477503",
        name: "Jan Mysak",
        position: "LW",
        number: 88,
        restGameTime: 320.4,
        restRealTime: 335.1,
        intermissionFlag: 0,
        shiftsThisPeriod: 0,
        shiftsTotalGame: 1,
        toiPast20min: 0.3,
        toiCumulativeGame: 1.2,
        ewmaShiftLength: 42.8,
        ewmaRestLength: 245.6,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    defense: [
      {
        id: "8476853",
        name: "Jayden Struble",
        position: "D",
        number: 47,
        restGameTime: 145.6,
        restRealTime: 152.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 9,
        toiPast20min: 4.7,
        toiCumulativeGame: 8.9,
        ewmaShiftLength: 46.8,
        ewmaRestLength: 98.3,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8475883",
        name: "David Savard",
        position: "D",
        number: 58,
        restGameTime: 88.9,
        restRealTime: 94.7,
        intermissionFlag: 0,
        shiftsThisPeriod: 6,
        shiftsTotalGame: 18,
        toiPast20min: 9.8,
        toiCumulativeGame: 15.6,
        ewmaShiftLength: 49.1,
        ewmaRestLength: 82.4,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8475279",
        name: "Kaiden Guhle",
        position: "D",
        number: 13,
        restGameTime: 185.2,
        restRealTime: 198.7,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 6,
        toiPast20min: 3.4,
        toiCumulativeGame: 7.1,
        ewmaShiftLength: 45.3,
        ewmaRestLength: 132.8,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477970",
        name: "Arber Xhekaj",
        position: "D",
        number: 72,
        restGameTime: 145.8,
        restRealTime: 159.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 11,
        toiPast20min: 5.2,
        toiCumulativeGame: 9.8,
        ewmaShiftLength: 47.6,
        ewmaRestLength: 105.4,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8479374",
        name: "Johnathan Kovacevic",
        position: "D",
        number: 26,
        restGameTime: 275.6,
        restRealTime: 289.1,
        intermissionFlag: 0,
        shiftsThisPeriod: 0,
        shiftsTotalGame: 3,
        toiPast20min: 0.9,
        toiCumulativeGame: 2.8,
        ewmaShiftLength: 43.7,
        ewmaRestLength: 198.3,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ]
  }
}

const mockOppRoster = {
  onIce: {
    forwards: [
      { id: "8478398", name: "Brad Marchand", position: "LW", number: 63 },
      { id: "8473419", name: "Brad Marchand", position: "C", number: 37 },
      { id: "8471276", name: "David Pastrnak", position: "RW", number: 88 }
    ],
    defense: [
      { id: "8471709", name: "Charlie McAvoy", position: "D", number: 73 },
      { id: "8476891", name: "Matt Grzelcyk", position: "D", number: 48 }
    ],
    goalie: { id: "8471695", name: "Jeremy Swayman", position: "G", number: 1 }
  },
  bench: {
    forwards: [
      {
        id: "8475762",
        name: "Charlie Coyle",
        position: "C",
        number: 13,
        restGameTime: 125.8,
        restRealTime: 138.4,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 10,
        toiPast20min: 4.7,
        toiCumulativeGame: 9.2,
        ewmaShiftLength: 42.3,
        ewmaRestLength: 95.6,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477956",
        name: "David Krejci",
        position: "C",
        number: 46,
        restGameTime: 95.2,
        restRealTime: 107.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 4,
        shiftsTotalGame: 13,
        toiPast20min: 6.1,
        toiCumulativeGame: 11.8,
        ewmaShiftLength: 39.8,
        ewmaRestLength: 78.9,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8478498",
        name: "Jake DeBrusk",
        position: "LW",
        number: 74,
        restGameTime: 75.6,
        restRealTime: 88.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 5,
        shiftsTotalGame: 16,
        toiPast20min: 7.8,
        toiCumulativeGame: 14.3,
        ewmaShiftLength: 41.7,
        ewmaRestLength: 72.4,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8473419",
        name: "Brad Marchand",
        position: "LW",
        number: 63,
        restGameTime: 65.4,
        restRealTime: 78.1,
        intermissionFlag: 0,
        shiftsThisPeriod: 6,
        shiftsTotalGame: 19,
        toiPast20min: 8.9,
        toiCumulativeGame: 16.7,
        ewmaShiftLength: 43.2,
        ewmaRestLength: 68.7,
        isWellRested: false,
        isOverused: true,
        isHeavyToi: true
      },
      {
        id: "8471276",
        name: "David Pastrnak",
        position: "RW",
        number: 88,
        restGameTime: 58.9,
        restRealTime: 71.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 7,
        shiftsTotalGame: 21,
        toiPast20min: 9.6,
        toiCumulativeGame: 18.4,
        ewmaShiftLength: 44.8,
        ewmaRestLength: 65.2,
        isWellRested: false,
        isOverused: true,
        isHeavyToi: true
      },
      {
        id: "8471217",
        name: "Trent Frederic",
        position: "C",
        number: 11,
        restGameTime: 185.7,
        restRealTime: 198.4,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 8,
        toiPast20min: 3.2,
        toiCumulativeGame: 7.1,
        ewmaShiftLength: 40.9,
        ewmaRestLength: 134.5,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8478398",
        name: "Morgan Geekie",
        position: "C",
        number: 39,
        restGameTime: 245.3,
        restRealTime: 258.7,
        intermissionFlag: 0,
        shiftsThisPeriod: 1,
        shiftsTotalGame: 5,
        toiPast20min: 1.9,
        toiCumulativeGame: 4.8,
        ewmaShiftLength: 38.6,
        ewmaRestLength: 178.9,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8477365",
        name: "Connor McDavid",
        position: "C",
        number: 97,
        restGameTime: 320.8,
        restRealTime: 335.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 0,
        shiftsTotalGame: 2,
        toiPast20min: 0.5,
        toiCumulativeGame: 1.7,
        ewmaShiftLength: 42.1,
        ewmaRestLength: 245.6,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    defense: [
      {
        id: "8475745",
        name: "Charlie McAvoy",
        position: "D",
        number: 33,
        restGameTime: 105.6,
        restRealTime: 118.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 4,
        shiftsTotalGame: 14,
        toiPast20min: 6.3,
        toiCumulativeGame: 12.8,
        ewmaShiftLength: 48.7,
        ewmaRestLength: 87.4,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8475744",
        name: "Connor Clifton",
        position: "D",
        number: 75,
        restGameTime: 155.8,
        restRealTime: 168.4,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 9,
        toiPast20min: 4.1,
        toiCumulativeGame: 8.7,
        ewmaShiftLength: 45.2,
        ewmaRestLength: 118.6,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8476891",
        name: "Matt Grzelcyk",
        position: "D",
        number: 48,
        restGameTime: 175.3,
        restRealTime: 187.9,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 7,
        toiPast20min: 3.8,
        toiCumulativeGame: 7.4,
        ewmaShiftLength: 46.8,
        ewmaRestLength: 128.7,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8471274",
        name: "Brandon Carlo",
        position: "D",
        number: 25,
        restGameTime: 135.7,
        restRealTime: 148.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 12,
        toiPast20min: 5.6,
        toiCumulativeGame: 10.9,
        ewmaShiftLength: 47.3,
        ewmaRestLength: 102.8,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ]
  }
}

// ENHANCED PREDICTIONS WITH BACKEND METRICS
const mockPredictions = [
  {
    id: "pred_1",
    probability: 0.324,
    confidence: 0.87,
    inferenceTimeMs: 8.7,
    matchupPrior: 0.15,
    chemistryScore: 0.82,
    fatigueScore: 0.23,
    forwards: ["8478398", "8473419", "8471276"],
    forwardsNames: ["Brad Marchand", "Pavel Zacha", "David Pastrnak"],
    defense: ["8471709", "8476891"],
    defenseNames: ["Charlie McAvoy", "Matt Grzelcyk"],
    explanation: "HIGH CONFIDENCE | OZ start - expect offensive lineup | Power play unit likely",
    riskAnalysis: {
      threatLevel: 0.75,
      matchupQuality: 0.68,
      expectedValue: 0.219
    }
  },
  {
    id: "pred_2",
    probability: 0.198,
    confidence: 0.72,
    inferenceTimeMs: 7.2,
    matchupPrior: -0.08,
    chemistryScore: 0.91,
    fatigueScore: 0.12,
    forwards: ["8475762", "8477956", "8478498"],
    forwardsNames: ["Charlie Coyle", "David Krejci", "Jake DeBrusk"],
    defense: ["8475745", "8475744"],
    defenseNames: ["Brandon Carlo", "Connor Clifton"],
    explanation: "MODERATE CONFIDENCE | DZ start - expect defensive lineup | Fresh legs available",
    riskAnalysis: {
      threatLevel: 0.42,
      matchupQuality: 0.79,
      expectedValue: 0.157
    }
  },
  {
    id: "pred_3",
    probability: 0.156,
    confidence: 0.65,
    inferenceTimeMs: 9.1,
    matchupPrior: 0.22,
    chemistryScore: 0.74,
    fatigueScore: 0.31,
    forwards: ["8478398", "8473419", "8478498"],
    forwardsNames: ["Brad Marchand", "Pavel Zacha", "Jake DeBrusk"],
    defense: ["8471709", "8476891"],
    defenseNames: ["Charlie McAvoy", "Matt Grzelcyk"],
    explanation: "MODERATE CONFIDENCE | Chemistry trio | Trailing late - offensive push expected",
    riskAnalysis: {
      threatLevel: 0.88,
      matchupQuality: 0.45,
      expectedValue: 0.070
    }
  }
]

// STRATEGIC ANALYSIS FROM BACKEND
const mockStrategicAnalysis = {
  scenario: "opponent_has_last_change",
  strategicAdvantage: "OPPONENT",
  confidence: 0.78,
  inferenceTimeMs: 245.3,
  mtlDeploymentOptions: [
    {
      players: ["8480018", "8479318", "8481540", "8476875", "8482087"],
      playersNames: ["Caufield", "Dach", "Dvorak", "Matheson", "Guhle"],
      probabilityPrior: 0.324,
      matchupPrior: 0.15,
      chemistryScore: 0.82,
      fatigueScore: 0.23,
      riskLevel: "MEDIUM"
    },
    {
      players: ["8476458", "8479318", "8477476", "8475883", "8476853"],
      playersNames: ["Slafkovsky", "Dach", "Anderson", "Savard", "Struble"],
      probabilityPrior: 0.198,
      matchupPrior: -0.08,
      chemistryScore: 0.91,
      fatigueScore: 0.12,
      riskLevel: "LOW"
    }
  ],
  riskAnalysis: [
    {
      mtlDeployment: ["8480018", "8479318", "8481540", "8476875", "8482087"],
      mtlNames: ["Caufield", "Dach", "Dvorak", "Matheson", "Guhle"],
      opponentCounterResponses: [
        {
          players: ["8478398", "8473419", "8471276", "8471709", "8476891"],
          playersNames: ["Marchand", "Zacha", "Pastrnak", "McAvoy", "Grzelcyk"],
          probability: 0.324,
          threatLevel: 0.75,
          matchupQuality: 0.68
        },
        {
          players: ["8475762", "8477956", "8478498", "8475745", "8475744"],
          playersNames: ["Coyle", "Krejci", "DeBrusk", "Carlo", "Clifton"],
          probability: 0.198,
          threatLevel: 0.42,
          matchupQuality: 0.79
        }
      ]
    }
  ],
  strategicRecommendation: {
    mtlDeployment: ["8476458", "8479318", "8477476", "8475883", "8476853"],
    mtlNames: ["Slafkovsky", "Dach", "Anderson", "Savard", "Struble"],
    expectedValue: 0.157,
    riskLevel: "LOW",
    reasoning: "Lowest opponent threat level with solid matchup quality"
  }
}

// PERFORMANCE METRICS FROM BACKEND
const mockPerformanceMetrics = {
  totalPredictions: 1247,
  avgLatencyMs: 8.7,
  p95LatencyMs: 12.3,
  maxLatencyMs: 45.2,
  avgConfidence: 0.76,
  recentPredictions: 89,
  systemUptime: 99.7,
  modelAccuracy: 87.3,
  predictionsPerSecond: 12.4,
  memoryUsage: 2.1,
  cacheSize: 156,
  temperature: 1.05
}

const mockChangeHistory = [
  {
    id: "change-001",
    period: 1,
    time: "12:34",
    type: "forward_line" as const,
    changeType: "line_change" as const,
    oldLine: "4TH LINE",
    newLine: "2ND LINE",
    playersOut: ["Joel Armia", "Jake Evans", "Rafael Harvey-Pinard"],
    playersIn: ["Josh Anderson", "Nick Suzuki", "Juraj Slafkovsky"],
    reason: "Fatigue management - 4th line heavy TOI"
  },
  {
    id: "change-002",
    period: 1,
    time: "8:45",
    type: "defense_pairing" as const,
    changeType: "power_play" as const,
    oldLine: "2ND PAIRING",
    newLine: "1ST PAIRING",
    playersOut: ["Jordan Harris", "David Savard"],
    playersIn: ["Michael Matheson", "Kaiden Guhle"],
    reason: "Power play opportunity"
  },
  {
    id: "change-003",
    period: 2,
    time: "15:22",
    type: "forward_line" as const,
    changeType: "penalty_kill" as const,
    oldLine: "3RD LINE",
    newLine: "1ST LINE",
    playersOut: ["Christian Dvorak", "Alex Newhook", "Jesse Ylonen"],
    playersIn: ["Nick Suzuki", "Cole Caufield", "Kirby Dach"],
    reason: "Penalty kill activation"
  },
  {
    id: "change-004",
    period: 2,
    time: "7:18",
    type: "defense_pairing" as const,
    changeType: "rest" as const,
    oldLine: "1ST PAIRING",
    newLine: "3RD PAIRING",
    playersOut: ["Michael Matheson", "Kaiden Guhle"],
    playersIn: ["Johnathan Kovacevic", "Arber Xhekaj"],
    reason: "Rest period for top pairing"
  },
  {
    id: "change-005",
    period: 2,
    time: "3:45",
    type: "forward_line" as const,
    changeType: "injury" as const,
    oldLine: "2ND LINE",
    newLine: "SCRATCH LINE",
    playersOut: ["Josh Anderson", "Juraj Slafkovsky", "Brendan Gallagher"],
    playersIn: ["Joel Armia", "Jake Evans", "Rafael Harvey-Pinard"],
    reason: "Gallagher injury concern"
  },
  {
    id: "change-006",
    period: 3,
    time: "18:33",
    type: "defense_pairing" as const,
    changeType: "line_change" as const,
    oldLine: "3RD PAIRING",
    newLine: "1ST PAIRING",
    playersOut: ["Johnathan Kovacevic", "Arber Xhekaj"],
    playersIn: ["Michael Matheson", "Kaiden Guhle"],
    reason: "Clutch defensive pairing activation"
  }
]

export default function PulsePage() {
  const [gameData, setGameData] = useState(mockGameData)
  const [mtlRoster, setMtlRoster] = useState(mockMtlRoster)
  const [oppRoster, setOppRoster] = useState(mockOppRoster)
  const [predictions, setPredictions] = useState(mockPredictions)
  const [strategicAnalysis, setStrategicAnalysis] = useState(mockStrategicAnalysis)
  const [performanceMetrics, setPerformanceMetrics] = useState(mockPerformanceMetrics)
  const [changeHistory, setChangeHistory] = useState(mockChangeHistory)
  const [isLoading, setIsLoading] = useState(false)

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      setGameData(prev => ({
        ...prev,
        periodTime: Math.max(0, prev.periodTime - 0.01),
        gameTime: prev.gameTime + 0.01
      }))
    }, 1000)

    return () => clearInterval(interval)
  }, [])

  return (
    <BasePage loadingMessage="CONNECTING TO PULSE MATRIX...">
      <div className="min-h-screen bg-gray-950 relative overflow-hidden">
        {/* Matrix-style background animation */}
        <div className="absolute inset-0 opacity-10">
          <div className="matrix-rain"></div>
        </div>

        {/* Main content */}
        <div className="relative z-10 p-2 sm:p-4 lg:p-6 space-y-4 lg:space-y-6 max-w-screen-2xl pt-20">
          {/* App Header */}
          <div className="fixed top-0 left-0 right-0 z-50 bg-black/80 backdrop-blur-md border-b border-gray-700/30 py-4 text-center">
            <h1 className="text-3xl font-military-display text-white tracking-wider">
              HeartBeat
            </h1>
          </div>

          {/* Top Row - Scoreboard and Phase Indicators */}
          <div className="w-full">
            <div className="flex flex-col lg:flex-row gap-4 lg:gap-6 w-full">
          {/* Game Dashboard - Live Score and Status */}
              <div className="flex-1">
          <PulseGameDashboard gameData={gameData} />
              </div>

              {/* Phase Indicators */}
              <div className="flex-1">
                <PulsePhaseIndicators gameData={gameData} />
              </div>
            </div>
          </div>

          {/* On-Ice Formation - Main Center Stage */}
          <div className="w-full">
            <PulseOnIceFormation
              homeRoster={mtlRoster}
              awayRoster={oppRoster}
              homeTeam="MONTREAL CANADIENS"
              awayTeam="BOSTON BRUINS"
            />
          </div>

          {/* Analysis Section - Optimized Layout */}
          <div className="flex flex-col xl:flex-row gap-6">
            {/* Left Side Content - Primary Analytics */}
            <div className="flex-[2] space-y-6">
              {/* Montreal Bench Roster */}
              <PulseUnifiedRoster
              title="MONTREAL CANADIENS"
                subtitle="BENCH PLAYERS"
              roster={mtlRoster}
              isHome={true}
            />

              {/* Prediction Engine */}
              <PulseAdvancedPrediction
                predictions={predictions}
                gameData={gameData}
              />

              {/* Strategic Analysis */}
              <PulseStrategicAnalysis
                strategicAnalysis={strategicAnalysis}
                gameData={gameData}
              />

              {/* Enhanced Metrics Stream */}
              <PulseMetricsStream performanceMetrics={performanceMetrics} />

              {/* Boston Bench Roster */}
              <PulseUnifiedRoster
              title="BOSTON BRUINS"
                subtitle="BENCH PLAYERS"
              roster={oppRoster}
              isHome={false}
              />
            </div>

            {/* Right Side - Secondary Content */}
            <div className="flex-[1] space-y-6">
              {/* Player Change Log */}
              <PulsePlayerChangeLog changeHistory={changeHistory} />
            </div>
          </div>


          {/* Status Footer */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-8"
          >
            <div className="inline-flex items-center space-x-4 bg-gray-900/60 border border-gray-700 rounded-lg px-4 py-2">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-red-400">LIVE FEED ACTIVE</span>
              </div>
              <div className="w-px h-4 bg-gray-600"></div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-red-400">PREDICTION ENGINE ONLINE</span>
              </div>
              <div className="w-px h-4 bg-gray-600"></div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-gray-400">NEURAL MATRIX SYNC</span>
              </div>
            </div>
          </motion.div>
        </div>
      </div>

      <style jsx>{`
        .matrix-rain {
          position: absolute;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(180deg, #000 0%, #111 100%);
          overflow: hidden;
        }

        .matrix-rain::before {
          content: '0101001001010010010100100101001001010010';
          position: absolute;
          top: -100%;
          left: 0;
          width: 100%;
          height: 200%;
          font-family: 'Courier New', monospace;
          font-size: 12px;
          color: #666666;
          opacity: 0.1;
          animation: matrix-fall 10s linear infinite;
          white-space: pre;
          line-height: 1.2;
        }

        @keyframes matrix-fall {
          0% { transform: translateY(-100%); }
          100% { transform: translateY(100%); }
        }
      `}</style>

    </BasePage>
  )
}
