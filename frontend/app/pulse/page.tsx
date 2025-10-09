'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { BasePage } from '../../components/layout/BasePage'
import { PulseCompactHeader } from '../../components/pulse/PulseCompactHeader'
import { PulseAdvancedPrediction } from '../../components/pulse/PulseAdvancedPrediction'
import { PulseUnifiedRoster } from '../../components/pulse/PulseUnifiedRoster'
import { PulseStrategicAnalysis } from '../../components/pulse/PulseStrategicAnalysis'
import { PulseOnIceFormation } from '../../components/pulse/PulseOnIceFormation'
import { PulsePlayerChangeLog } from '../../components/pulse/PulsePlayerChangeLog'
import { PulseAvailablePlayersMatrix } from '../../components/pulse/PulseAvailablePlayersMatrix'

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
        id: "8480000",
        name: "Brendan Gallagher",
        position: "RW",
        number: 11,
        restGameTime: 88.6,
        restRealTime: 95.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 5,
        shiftsTotalGame: 16,
        toiPast20min: 7.8,
        toiCumulativeGame: 13.4,
        ewmaShiftLength: 41.2,
        ewmaRestLength: 82.3,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8480001",
        name: "Jake Evans",
        position: "C",
        number: 71,
        restGameTime: 145.8,
        restRealTime: 158.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 3,
        shiftsTotalGame: 9,
        toiPast20min: 4.2,
        toiCumulativeGame: 8.7,
        ewmaShiftLength: 39.5,
        ewmaRestLength: 105.8,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8480002",
        name: "Alex Newhook",
        position: "C",
        number: 15,
        restGameTime: 112.4,
        restRealTime: 125.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 4,
        shiftsTotalGame: 11,
        toiPast20min: 5.6,
        toiCumulativeGame: 10.2,
        ewmaShiftLength: 40.3,
        ewmaRestLength: 92.7,
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
      },
    ]
  }
}

const mockOppRoster = {
  onIce: {
    forwards: [
      { 
        id: "8473419", 
        name: "Brad Marchand", 
        position: "LW", 
        number: 63,
        restGameTime: 0,
        restRealTime: 0,
        intermissionFlag: 0,
        shiftsThisPeriod: 8,
        shiftsTotalGame: 22,
        toiPast20min: 11.5,
        toiCumulativeGame: 17.8,
        ewmaShiftLength: 41.2,
        ewmaRestLength: 75.3,
        isWellRested: false,
        isOverused: false,
        isHeavyToi: false
      },
      { 
        id: "8478460", 
        name: "Pavel Zacha", 
        position: "C", 
        number: 18,
        restGameTime: 0,
        restRealTime: 0,
        intermissionFlag: 0,
        shiftsThisPeriod: 7,
        shiftsTotalGame: 19,
        toiPast20min: 10.2,
        toiCumulativeGame: 15.6,
        ewmaShiftLength: 39.8,
        ewmaRestLength: 82.1,
        isWellRested: false,
        isOverused: false,
        isHeavyToi: false
      },
      { 
        id: "8471276", 
        name: "David Pastrnak", 
        position: "RW", 
        number: 88,
        restGameTime: 0,
        restRealTime: 0,
        intermissionFlag: 0,
        shiftsThisPeriod: 9,
        shiftsTotalGame: 25,
        toiPast20min: 13.1,
        toiCumulativeGame: 19.4,
        ewmaShiftLength: 43.5,
        ewmaRestLength: 68.7,
        isWellRested: false,
        isOverused: true,
        isHeavyToi: true
      }
    ],
    defense: [
      { 
        id: "8471709", 
        name: "Charlie McAvoy", 
        position: "D", 
        number: 73,
        restGameTime: 0,
        restRealTime: 0,
        intermissionFlag: 0,
        shiftsThisPeriod: 11,
        shiftsTotalGame: 29,
        toiPast20min: 14.8,
        toiCumulativeGame: 22.3,
        ewmaShiftLength: 47.2,
        ewmaRestLength: 71.5,
        isWellRested: false,
        isOverused: false,
        isHeavyToi: false
      },
      { 
        id: "8476891", // Matt Grzelcyk - Real ID from player_ids.csv
        name: "Matt Grzelcyk", 
        position: "D", 
        number: 48,
        restGameTime: 0,
        restRealTime: 0,
        intermissionFlag: 0,
        shiftsThisPeriod: 8,
        shiftsTotalGame: 21,
        toiPast20min: 11.2,
        toiCumulativeGame: 16.8,
        ewmaShiftLength: 44.1,
        ewmaRestLength: 85.3,
        isWellRested: false,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    goalie: { 
      id: "8471695", 
      name: "Jeremy Swayman", 
      position: "G", 
      number: 1,
      restGameTime: 1200.0,
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
        id: "8480010",
        name: "Matthew Poitras",
        position: "C",
        number: 51,
        restGameTime: 165.4,
        restRealTime: 178.1,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 7,
        toiPast20min: 3.9,
        toiCumulativeGame: 8.7,
        ewmaShiftLength: 39.2,
        ewmaRestLength: 128.7,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
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
        id: "8480011",
        name: "Johnny Beecher",
        position: "C",
        number: 19,
        restGameTime: 195.8,
        restRealTime: 208.2,
        intermissionFlag: 0,
        shiftsThisPeriod: 1,
        shiftsTotalGame: 4,
        toiPast20min: 1.5,
        toiCumulativeGame: 3.7,
        ewmaShiftLength: 37.1,
        ewmaRestLength: 165.6,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8480012",
        name: "James van Riemsdyk",
        position: "LW",
        number: 21,
        restGameTime: 155.4,
        restRealTime: 168.8,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 6,
        toiPast20min: 2.8,
        toiCumulativeGame: 5.9,
        ewmaShiftLength: 36.4,
        ewmaRestLength: 118.3,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8480013",
        name: "Danton Heinen",
        position: "LW",
        number: 43,
        restGameTime: 215.7,
        restRealTime: 228.3,
        intermissionFlag: 0,
        shiftsThisPeriod: 1,
        shiftsTotalGame: 3,
        toiPast20min: 1.2,
        toiCumulativeGame: 2.8,
        ewmaShiftLength: 35.8,
        ewmaRestLength: 175.4,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      }
    ],
    defense: [
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
        id: "8480014",
        name: "Derek Forbort",
        position: "D",
        number: 28,
        restGameTime: 188.3,
        restRealTime: 201.7,
        intermissionFlag: 0,
        shiftsThisPeriod: 2,
        shiftsTotalGame: 6,
        toiPast20min: 2.8,
        toiCumulativeGame: 5.9,
        ewmaShiftLength: 42.8,
        ewmaRestLength: 145.7,
        isWellRested: true,
        isOverused: false,
        isHeavyToi: false
      },
      {
        id: "8480015",
        name: "Mason Lohrei",
        position: "D",
        number: 6,
        restGameTime: 225.5,
        restRealTime: 238.9,
        intermissionFlag: 0,
        shiftsThisPeriod: 1,
        shiftsTotalGame: 4,
        toiPast20min: 1.4,
        toiCumulativeGame: 3.2,
        ewmaShiftLength: 40.1,
        ewmaRestLength: 168.3,
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
        {/* Animated background grid */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute inset-0" style={{
            backgroundImage: `
              linear-gradient(rgba(6, 182, 212, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(6, 182, 212, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px'
          }} />
        </div>

        {/* Radial gradient overlay */}
        <div className="absolute inset-0 bg-gradient-radial from-red-600/5 via-transparent to-transparent opacity-30" />

        {/* Main content - Centered Layout */}
        <div className="relative z-10 mx-auto max-w-screen-2xl px-6 pt-4 pb-20 lg:px-12">
          {/* Header */}
          <div className="mb-6 py-2 text-center">
            <h1 className="text-3xl font-military-display text-white tracking-wider">
              HeartBeat
            </h1>
          </div>

          {/* Compact Game Header - Merged Dashboard + Phase Indicators */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, type: "spring", damping: 20 }}
            className="mb-12 flex justify-center"
          >
            <div className="w-full">
              <PulseCompactHeader gameData={gameData} />
            </div>
          </motion.div>

          {/* Main On-Ice Formation - Centered Showcase with Side Matrices */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-16 relative"
          >
            {/* Container for rink + matrices */}
            <div className="relative flex items-center justify-center gap-16">
              {/* Away Team Available Players - Left */}
              <div className="flex-shrink-0">
                <PulseAvailablePlayersMatrix
                  roster={oppRoster}
                  isHome={false}
                />
              </div>

              {/* Rink */}
              <div className="flex-1 max-w-5xl">
                <PulseOnIceFormation
                  homeRoster={mtlRoster}
                  awayRoster={oppRoster}
                  homeTeam="MONTREAL CANADIENS"
                  awayTeam="BOSTON BRUINS"
                  period={gameData.period}
                  periodTime={gameData.periodTime}
                />
              </div>

              {/* Home Team Available Players - Right */}
              <div className="flex-shrink-0">
                <PulseAvailablePlayersMatrix
                  roster={mtlRoster}
                  isHome={true}
                />
              </div>
            </div>
          </motion.div>

          {/* Teams Comparison Section - Side by Side */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mb-16"
          >
            <div className="flex items-center space-x-2 mb-6">
              <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
              <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                Bench Rosters
              </h3>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* Boston Team Section - Left (Away) */}
              <div className="space-y-6">
                <PulseUnifiedRoster
                  title="BOSTON BRUINS"
                  subtitle="BENCH PLAYERS"
                  roster={oppRoster}
                  isHome={false}
                />
              </div>

              {/* Montreal Team Section - Right (Home) */}
              <div className="space-y-6">
                <PulseUnifiedRoster
                  title="MONTREAL CANADIENS"
                  subtitle="BENCH PLAYERS"
                  roster={mtlRoster}
                  isHome={true}
                />
              </div>
            </div>
          </motion.div>

          {/* Analytics Section - Centered Layout */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="space-y-16"
          >
            {/* Prediction Engine - Full Width */}
            <div>
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                  Prediction Engine
                </h3>
              </div>
              <PulseAdvancedPrediction
                predictions={predictions}
                gameData={gameData}
              />
            </div>

            {/* Strategic Analysis and Change Log - Side by Side */}
            <div>
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-0.5 h-4 bg-gradient-to-b from-white to-transparent" />
                <h3 className="text-xs font-military-display text-white uppercase tracking-widest">
                  Tactical Intelligence
                </h3>
              </div>
              <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
                {/* Strategic Analysis - Takes up 2/3 on large screens */}
                <div className="xl:col-span-2">
                  <PulseStrategicAnalysis
                    strategicAnalysis={strategicAnalysis}
                    gameData={gameData}
                  />
                </div>

                {/* Player Change Log - Takes up 1/3 on large screens */}
                <div className="xl:col-span-1">
                  <PulsePlayerChangeLog changeHistory={changeHistory} />
                </div>
              </div>
            </div>
          </motion.div>

          {/* Status Footer - Centered */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-16 text-center"
          >
            <div className="inline-flex items-center space-x-4 bg-black/40 backdrop-blur-xl border border-white/10 rounded-lg px-6 py-3 shadow-xl shadow-white/5">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-red-400 tracking-wider">LIVE FEED ACTIVE</span>
              </div>
              <div className="w-px h-4 bg-white/10"></div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-red-600 rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-red-400 tracking-wider">PREDICTION ENGINE ONLINE</span>
              </div>
              <div className="w-px h-4 bg-white/10"></div>
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                <span className="text-xs font-military-display text-white tracking-wider">NEURAL MATRIX SYNC</span>
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
