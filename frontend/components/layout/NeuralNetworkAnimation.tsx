'use client'

import { useEffect, useRef, useState, useMemo } from 'react'
import * as THREE from 'three'
import * as CANNON from 'cannon-es'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'
import { ShaderPass } from 'three/examples/jsm/postprocessing/ShaderPass.js'
import * as TWEEN from '@tweenjs/tween.js'

interface NeuralNetworkAnimationProps {
  className?: string
  games?: GameData[]
  selectedGameId?: string
  onGameSelect?: (gameId: string) => void
}

interface GameEvent {
  id: string
  type: 'faceoff' | 'pass' | 'shot' | 'save' | 'goal' | 'hit' | 'takeaway' | 'penalty' | 'period' | 'player' | 'rebound' | 'block' | 'miss'
  label: string
  sequence: number
  period?: number
  timestamp?: number
  players?: string[]
  zone?: 'offensive' | 'defensive' | 'neutral'
  outcome?: 'success' | 'failure' | 'neutral'
  relatedEvents?: string[] // IDs of related events
  thematicGroups?: string[] // Groups like 'shots', 'goals', 'powerplay', etc.
}

interface PlayerNode {
  id: string
  name: string
  team: 'home' | 'away'
  jerseyNumber: string
  position: string
  connections: string[] // IDs of other players this player has interacted with
  interactionCount: number // Number of interactions
}

interface GameData {
  id: string
  homeTeam: string
  awayTeam: string
  homeScore: number
  awayScore: number
  date: string
  events: GameEvent[]
  homeRoster: PlayerNode[]
  awayRoster: PlayerNode[]
}

interface ParticleData {
  id: string
  position: THREE.Vector3
  velocity: THREE.Vector3
  size: number
  color: { r: number, g: number, b: number }
  playerId: string
  team: 'home' | 'away'
  jerseyNumber: string
  name: string
  connections: string[] // Connected player IDs
  clusterPosition: THREE.Vector3
  gameId: string
  numConnections: number // For animation physics
  physicsBody?: CANNON.Body // Physics integration
  energy: number // Energy level for visual effects
  trail: THREE.Vector3[] // Particle trail for motion blur
}

// Advanced Shaders for Futuristic Effects
const ParticleVertexShader = `
  attribute float size;
  attribute float energy;
  attribute float alpha;

  varying vec3 vColor;
  varying float vEnergy;
  varying float vAlpha;
  varying vec3 vPosition;

  uniform float time;
  uniform float pixelRatio;

  void main() {
    vColor = color;
    vEnergy = energy;
    vAlpha = alpha;
    vPosition = position;

    vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);

    // Dynamic size based on energy and distance
    float finalSize = size * (1.0 + energy * 0.5) * pixelRatio;
    finalSize *= (300.0 / -mvPosition.z);

    gl_PointSize = finalSize;
    gl_Position = projectionMatrix * mvPosition;
  }
`

const ParticleFragmentShader = `
  varying vec3 vColor;
  varying float vEnergy;
  varying float vAlpha;
  varying vec3 vPosition;

  uniform float time;

  // Noise function for organic effects
  float noise(vec3 p) {
    return fract(sin(dot(p, vec3(12.9898, 78.233, 45.164))) * 43758.5453);
  }

  void main() {
    // Create circular particle with energy-based glow
    vec2 center = gl_PointCoord - vec2(0.5);
    float dist = length(center);

    if (dist > 0.5) discard;

    // Energy-based glow effect
    float glow = 1.0 - smoothstep(0.0, 0.5, dist);
    glow *= (1.0 + vEnergy * 0.8);

    // Pulsing effect
    float pulse = sin(time * 2.0 + vPosition.x * 0.01 + vPosition.y * 0.01) * 0.3 + 0.7;
    glow *= pulse;

    // Noise for organic texture
    float n = noise(vPosition * 0.1 + time * 0.1);
    glow *= (0.8 + n * 0.4);

    vec3 finalColor = vColor * glow;

    gl_FragColor = vec4(finalColor, vAlpha * glow);
  }
`

const ConnectionVertexShader = `
  attribute float alpha;

  varying vec3 vColor;
  varying float vAlpha;
  varying vec3 vPosition;

  uniform float time;

  void main() {
    vColor = color;
    vAlpha = alpha;
    vPosition = position;

    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`

const ConnectionFragmentShader = `
  varying vec3 vColor;
  varying float vAlpha;
  varying vec3 vPosition;

  uniform float time;

  void main() {
    // Create energy flow effect along connection lines
    float flow = sin(vPosition.x * 0.1 + time * 3.0) * 0.5 + 0.5;
    float glow = flow * vAlpha;

    // Add some noise for organic feel
    float noise = sin(vPosition.y * 0.05 + time * 2.0) * 0.2 + 0.8;
    glow *= noise;

    vec3 finalColor = vColor * glow;

    gl_FragColor = vec4(finalColor, glow);
  }
`

// Simple OrbitControls implementation
class SimpleOrbitControls {
  camera: THREE.PerspectiveCamera
  domElement: HTMLElement
  target = new THREE.Vector3()
  
  spherical = new THREE.Spherical()
  sphericalDelta = new THREE.Spherical()
  
  scale = 1
  panOffset = new THREE.Vector3()
  zoomChanged = false
  
  rotateSpeed = 1.2
  zoomSpeed = 1.0
  
  mouseButtons = { LEFT: 0, MIDDLE: 1, RIGHT: 2 }

  // Enhanced rotation for better 360 experience
  minPolarAngle = 0.1
  maxPolarAngle = Math.PI - 0.1
  enableZoom = true
  enableRotate = true
  enablePan = true

  // Inertia for smoother movement
  private velocity = new THREE.Vector2()
  private damping = 0.85
  
  private rotateStart = new THREE.Vector2()
  private rotateEnd = new THREE.Vector2()
  private rotateDelta = new THREE.Vector2()
  
  private isMouseDown = false
  
  // Store bound functions for cleanup
  private boundOnMouseDown: (e: MouseEvent) => void
  private boundOnMouseMove: (e: MouseEvent) => void
  private boundOnMouseUp: (e: MouseEvent) => void
  private boundOnMouseWheel: (e: WheelEvent) => void
  private boundOnTouchStart: (e: TouchEvent) => void
  private boundOnTouchMove: (e: TouchEvent) => void
  private boundOnTouchEnd: (e: TouchEvent) => void
  
  constructor(camera: THREE.PerspectiveCamera, domElement: HTMLElement) {
    this.camera = camera
    this.domElement = domElement
    
    // Bind methods and store references
    this.boundOnMouseDown = this.onMouseDown.bind(this)
    this.boundOnMouseMove = this.onMouseMove.bind(this)
    this.boundOnMouseUp = this.onMouseUp.bind(this)
    this.boundOnMouseWheel = this.onMouseWheel.bind(this)
    this.boundOnTouchStart = this.onTouchStart.bind(this)
    this.boundOnTouchMove = this.onTouchMove.bind(this)
    this.boundOnTouchEnd = this.onTouchEnd.bind(this)
    
    // Add event listeners
    this.domElement.addEventListener('mousedown', this.boundOnMouseDown)
    this.domElement.addEventListener('mousemove', this.boundOnMouseMove)
    this.domElement.addEventListener('mouseup', this.boundOnMouseUp)
    this.domElement.addEventListener('mouseleave', this.boundOnMouseUp)
    this.domElement.addEventListener('wheel', this.boundOnMouseWheel, { passive: false })
    this.domElement.addEventListener('contextmenu', (e) => e.preventDefault())

    // Touch support for mobile
    this.domElement.addEventListener('touchstart', this.boundOnTouchStart, { passive: false })
    this.domElement.addEventListener('touchmove', this.boundOnTouchMove, { passive: false })
    this.domElement.addEventListener('touchend', this.boundOnTouchEnd, { passive: false })
    
    this.update()
  }
  
  onMouseDown(event: MouseEvent) {
    event.preventDefault()
    event.stopPropagation()
    this.isMouseDown = true
    this.rotateStart.set(event.clientX, event.clientY)
    console.log('Mouse down at:', event.clientX, event.clientY)
  }
  
  onMouseMove(event: MouseEvent) {
    if (!this.isMouseDown) return
    
    event.preventDefault()
    event.stopPropagation()
    
    this.rotateEnd.set(event.clientX, event.clientY)
    this.rotateDelta.subVectors(this.rotateEnd, this.rotateStart).multiplyScalar(this.rotateSpeed)
    
    const element = this.domElement
    this.rotateLeft(2 * Math.PI * this.rotateDelta.x / element.clientHeight)
    this.rotateUp(2 * Math.PI * this.rotateDelta.y / element.clientHeight)

    // Update velocity for inertia
    this.velocity.copy(this.rotateDelta).multiplyScalar(0.1)
    
    this.rotateStart.copy(this.rotateEnd)
    this.update()
  }
  
  onMouseUp(event: MouseEvent) {
    event.preventDefault()
    this.isMouseDown = false
  }

  onTouchStart(event: TouchEvent) {
    if (event.touches.length === 1) {
      event.preventDefault()
      event.stopPropagation()
      this.isMouseDown = true
      this.rotateStart.set(event.touches[0].clientX, event.touches[0].clientY)
    }
  }

  onTouchMove(event: TouchEvent) {
    if (!this.isMouseDown || event.touches.length !== 1) return

    event.preventDefault()
    event.stopPropagation()

    this.rotateEnd.set(event.touches[0].clientX, event.touches[0].clientY)
    this.rotateDelta.subVectors(this.rotateEnd, this.rotateStart).multiplyScalar(this.rotateSpeed)

    const element = this.domElement
    this.rotateLeft(2 * Math.PI * this.rotateDelta.x / element.clientHeight)
    this.rotateUp(2 * Math.PI * this.rotateDelta.y / element.clientHeight)

    // Update velocity for inertia
    this.velocity.copy(this.rotateDelta).multiplyScalar(0.05)

    this.rotateStart.copy(this.rotateEnd)
    this.update()
  }

  onTouchEnd(event: TouchEvent) {
    event.preventDefault()
    this.isMouseDown = false
  }
  
  onMouseWheel(event: WheelEvent) {
    event.preventDefault()
    event.stopPropagation()
    
    if (event.deltaY < 0) {
      this.dollyIn(this.getZoomScale())
    } else if (event.deltaY > 0) {
      this.dollyOut(this.getZoomScale())
    }
    
    this.update()
  }
  
  getZoomScale() {
    return Math.pow(0.95, this.zoomSpeed)
  }
  
  rotateLeft(angle: number) {
    this.sphericalDelta.theta -= angle
  }
  
  rotateUp(angle: number) {
    this.sphericalDelta.phi -= angle
  }
  
  dollyIn(dollyScale: number) {
    this.scale /= dollyScale
  }
  
  dollyOut(dollyScale: number) {
    this.scale *= dollyScale
  }
  
  update() {
    const offset = new THREE.Vector3()
    const quat = new THREE.Quaternion().setFromUnitVectors(
      this.camera.up,
      new THREE.Vector3(0, 1, 0)
    )
    const quatInverse = quat.clone().invert()
    
    const position = this.camera.position
    
    offset.copy(position).sub(this.target)
    offset.applyQuaternion(quat)
    
    this.spherical.setFromVector3(offset)
    
    this.spherical.theta += this.sphericalDelta.theta
    this.spherical.phi += this.sphericalDelta.phi
    
    // Apply inertia to rotation for smoother movement
    this.velocity.multiplyScalar(this.damping)
    this.spherical.theta += this.velocity.x * 0.01
    this.spherical.phi += this.velocity.y * 0.01

    // Allow full 360-degree rotation (no hard stops on theta)
    // Constrain phi (polar angle) to prevent camera flipping
    this.spherical.phi = Math.max(this.minPolarAngle, Math.min(this.maxPolarAngle, this.spherical.phi))

    // Normalize theta to keep it manageable (optional, for performance)
    this.spherical.theta %= Math.PI * 2
    
    this.spherical.radius *= this.scale
    this.spherical.radius = Math.max(400, Math.min(2500, this.spherical.radius))
    
    this.target.add(this.panOffset)
    
    offset.setFromSpherical(this.spherical)
    offset.applyQuaternion(quatInverse)
    
    position.copy(this.target).add(offset)
    
    this.camera.lookAt(this.target)
    
    this.sphericalDelta.set(0, 0, 0)
    this.panOffset.set(0, 0, 0)
    
    this.scale = 1
  }
  
  dispose() {
    this.domElement.removeEventListener('mousedown', this.boundOnMouseDown)
    this.domElement.removeEventListener('mousemove', this.boundOnMouseMove)
    this.domElement.removeEventListener('mouseup', this.boundOnMouseUp)
    this.domElement.removeEventListener('mouseleave', this.boundOnMouseUp)
    this.domElement.removeEventListener('wheel', this.boundOnMouseWheel)
    this.domElement.removeEventListener('touchstart', this.boundOnTouchStart)
    this.domElement.removeEventListener('touchmove', this.boundOnTouchMove)
    this.domElement.removeEventListener('touchend', this.boundOnTouchEnd)
  }
}

export function NeuralNetworkAnimation({
  className = '',
  games,
  selectedGameId,
  onGameSelect
}: NeuralNetworkAnimationProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const labelsContainerRef = useRef<HTMLDivElement>(null)
  const [badges, setBadges] = useState<Array<{
    id: string
    x: number
    y: number
    type: 'player' | 'period' | 'faceoff' | 'pass' | 'shot' | 'save' | 'goal' | 'hit' | 'takeaway' | 'penalty' | 'rebound' | 'block' | 'miss' | 'player-stat' | 'team-metric' | 'game-flow'
    label: string
    visible: boolean
    gameId?: string
    team?: 'home' | 'away' // Add team property for styling
  }>>([])

  const [hoveredParticle, setHoveredParticle] = useState<{
    id: string
    name: string
    jerseyNumber: string
    team: 'home' | 'away'
    x: number
    y: number
  } | null>(null)


  
  const sceneRef = useRef<{
    scene?: THREE.Scene
    camera?: THREE.PerspectiveCamera
    renderer?: THREE.WebGLRenderer
    particles?: THREE.BufferGeometry
    pointCloud?: THREE.Points
    linesMesh?: THREE.LineSegments
    particlesData?: ParticleData[]
    particlePositions?: Float32Array
    positions?: Float32Array
    colors?: Float32Array
    animationId?: number
    controls?: SimpleOrbitControls
    // Advanced physics and effects
    physicsWorld?: CANNON.World
    composer?: EffectComposer
    particleMaterial?: THREE.ShaderMaterial
    connectionMaterial?: THREE.ShaderMaterial
    trailsGeometry?: THREE.BufferGeometry
    trailsMesh?: THREE.LineSegments
    energyField?: THREE.Points
    time: number
  }>({
    time: 0
  })

  // Default games data with interconnected event webs
  const defaultGames: GameData[] = [
    {
      id: 'mtl-tor-2024-01-15',
      homeTeam: 'MTL',
      awayTeam: 'TOR',
      homeScore: 3,
      awayScore: 2,
      date: '2024-01-15',
      homeRoster: [],
      awayRoster: [],
      events: [
        // Period markers
        { id: 'p1-start', type: 'period', label: 'Period 1', sequence: 0, period: 1, timestamp: 0, thematicGroups: ['periods'] },

        // Opening faceoff sequence
        { id: 'fo-1', type: 'faceoff', label: 'Faceoff Win - Suzuki', sequence: 1, period: 1, timestamp: 15, players: ['Suzuki'], zone: 'neutral', outcome: 'success', thematicGroups: ['faceoffs', 'offensive-zone-starts'] },
        { id: 'pass-1', type: 'pass', label: 'Pass - Suzuki to Caufield', sequence: 2, period: 1, timestamp: 18, players: ['Suzuki', 'Caufield'], zone: 'offensive', outcome: 'success', relatedEvents: ['fo-1'], thematicGroups: ['passes', 'offensive-plays'] },
        { id: 'shot-1', type: 'shot', label: 'Shot - Caufield', sequence: 3, period: 1, timestamp: 20, players: ['Caufield'], zone: 'offensive', outcome: 'failure', relatedEvents: ['pass-1'], thematicGroups: ['shots', 'scoring-chances'] },
        { id: 'save-1', type: 'save', label: 'Save - Samsonov', sequence: 4, period: 1, timestamp: 21, players: ['Samsonov'], zone: 'defensive', outcome: 'success', relatedEvents: ['shot-1'], thematicGroups: ['saves', 'goaltending'] },

        // Defensive sequence
        { id: 'hit-1', type: 'hit', label: 'Hit - Matheson on Matthews', sequence: 5, period: 1, timestamp: 45, players: ['Matheson', 'Matthews'], zone: 'neutral', outcome: 'success', thematicGroups: ['hits', 'physical-play'] },
        { id: 'takeaway-1', type: 'takeaway', label: 'Takeaway - Dach', sequence: 6, period: 1, timestamp: 47, players: ['Dach'], zone: 'defensive', outcome: 'success', relatedEvents: ['hit-1'], thematicGroups: ['takeaways', 'defensive-plays'] },
        { id: 'pass-2', type: 'pass', label: 'Breakout Pass - Dach', sequence: 7, period: 1, timestamp: 50, players: ['Dach'], zone: 'defensive', outcome: 'success', relatedEvents: ['takeaway-1'], thematicGroups: ['passes', 'breakouts'] },

        // Goal sequence with full web of relationships
        { id: 'pass-3', type: 'pass', label: 'Pass - Matheson to Suzuki', sequence: 8, period: 1, timestamp: 240, players: ['Matheson', 'Suzuki'], zone: 'offensive', outcome: 'success', thematicGroups: ['passes', 'offensive-plays', 'pp1'] },
        { id: 'pass-4', type: 'pass', label: 'Pass - Suzuki to Caufield', sequence: 9, period: 1, timestamp: 243, players: ['Suzuki', 'Caufield'], zone: 'offensive', outcome: 'success', relatedEvents: ['pass-3'], thematicGroups: ['passes', 'offensive-plays', 'pp1'] },
        { id: 'shot-2', type: 'shot', label: 'Shot - Caufield', sequence: 10, period: 1, timestamp: 245, players: ['Caufield'], zone: 'offensive', outcome: 'success', relatedEvents: ['pass-4'], thematicGroups: ['shots', 'scoring-chances', 'pp1'] },
        { id: 'goal-1', type: 'goal', label: 'GOAL! Caufield (Suzuki, Matheson)', sequence: 11, period: 1, timestamp: 246, players: ['Caufield', 'Suzuki', 'Matheson'], zone: 'offensive', outcome: 'success', relatedEvents: ['shot-2', 'pass-4', 'pass-3'], thematicGroups: ['goals', 'powerplay-goals', 'pp1'] },

        // Period 2
        { id: 'p2-start', type: 'period', label: 'Period 2', sequence: 12, period: 2, timestamp: 1200, thematicGroups: ['periods'] },

        // Penalty sequence
        { id: 'hit-2', type: 'hit', label: 'Hit - Xhekaj on Marner', sequence: 13, period: 2, timestamp: 1350, players: ['Xhekaj', 'Marner'], zone: 'neutral', outcome: 'failure', thematicGroups: ['hits', 'physical-play', 'penalty-causes'] },
        { id: 'penalty-1', type: 'penalty', label: 'Penalty - Xhekaj (Roughing)', sequence: 14, period: 2, timestamp: 1351, players: ['Xhekaj'], zone: 'neutral', outcome: 'failure', relatedEvents: ['hit-2'], thematicGroups: ['penalties', 'powerplay-kills'] },

        // Power play defense sequence
        { id: 'fo-2', type: 'faceoff', label: 'PK Faceoff Win - Dvorak', sequence: 15, period: 2, timestamp: 1360, players: ['Dvorak'], zone: 'defensive', outcome: 'success', relatedEvents: ['penalty-1'], thematicGroups: ['faceoffs', 'penalty-kills'] },
        { id: 'pass-5', type: 'pass', label: 'Clear - Matheson', sequence: 16, period: 2, timestamp: 1365, players: ['Matheson'], zone: 'defensive', outcome: 'success', relatedEvents: ['fo-2'], thematicGroups: ['passes', 'penalty-kills'] },

        // Additional shots and rebounds to create web
        { id: 'shot-3', type: 'shot', label: 'Shot - Rielly (PP)', sequence: 17, period: 2, timestamp: 1380, players: ['Rielly'], zone: 'offensive', outcome: 'failure', thematicGroups: ['shots', 'powerplay-shots'] },
        { id: 'rebound-1', type: 'rebound', label: 'Rebound - Nylander', sequence: 18, period: 2, timestamp: 1381, players: ['Nylander'], zone: 'offensive', outcome: 'neutral', relatedEvents: ['shot-3'], thematicGroups: ['rebounds', 'powerplay-chances'] },
        { id: 'shot-4', type: 'shot', label: 'Shot - Nylander (PP)', sequence: 19, period: 2, timestamp: 1383, players: ['Nylander'], zone: 'offensive', outcome: 'failure', relatedEvents: ['rebound-1'], thematicGroups: ['shots', 'powerplay-shots'] },
        { id: 'save-2', type: 'save', label: 'Save - Allen', sequence: 20, period: 2, timestamp: 1384, players: ['Allen'], zone: 'defensive', outcome: 'success', relatedEvents: ['shot-4'], thematicGroups: ['saves', 'penalty-kills'] },

        // Player nodes for comprehensive web
        { id: 'player-suzuki', type: 'player', label: 'Suzuki #14', sequence: 100, period: 1, timestamp: 0, players: ['Suzuki'], thematicGroups: ['forwards', 'top-line'] },
        { id: 'player-caufield', type: 'player', label: 'Caufield #22', sequence: 101, period: 1, timestamp: 0, players: ['Caufield'], thematicGroups: ['forwards', 'top-line'] },
        { id: 'player-matheson', type: 'player', label: 'Matheson #8', sequence: 102, period: 1, timestamp: 0, players: ['Matheson'], thematicGroups: ['defensemen', 'top-pair'] },
        { id: 'player-dach', type: 'player', label: 'Dach #77', sequence: 103, period: 1, timestamp: 0, players: ['Dach'], thematicGroups: ['forwards', 'checking-line'] },
        { id: 'player-xhekaj', type: 'player', label: 'Xhekaj #75', sequence: 104, period: 2, timestamp: 0, players: ['Xhekaj'], thematicGroups: ['defensemen', 'physical-defenders'] },
      ]
    },
    {
      id: 'bos-nyr-2024-01-16',
      homeTeam: 'BOS',
      awayTeam: 'NYR',
      homeScore: 4,
      awayScore: 1,
      date: '2024-01-16',
      homeRoster: [],
      awayRoster: [],
      events: [
        { id: 'bos-p1', type: 'period', label: 'Period 1', sequence: 0, period: 1, timestamp: 0, thematicGroups: ['periods'] },
        { id: 'bos-goal-1', type: 'goal', label: 'GOAL! Marchand (PP)', sequence: 1, period: 1, timestamp: 125, players: ['Marchand'], zone: 'offensive', outcome: 'success', thematicGroups: ['goals', 'powerplay-goals'] },
        { id: 'bos-shot-1', type: 'shot', label: 'Shot - Zibanejad', sequence: 2, period: 1, timestamp: 340, players: ['Zibanejad'], zone: 'offensive', outcome: 'failure', thematicGroups: ['shots'] },
        { id: 'bos-save-1', type: 'save', label: 'Save - Swayman', sequence: 3, period: 1, timestamp: 341, players: ['Swayman'], zone: 'defensive', outcome: 'success', relatedEvents: ['bos-shot-1'], thematicGroups: ['saves'] },
        { id: 'bos-p2', type: 'period', label: 'Period 2', sequence: 4, period: 2, timestamp: 1200, thematicGroups: ['periods'] },
        { id: 'bos-goal-2', type: 'goal', label: 'GOAL! Pasta', sequence: 5, period: 2, timestamp: 1420, players: ['Pasta'], zone: 'offensive', outcome: 'success', thematicGroups: ['goals'] },
        { id: 'bos-goal-3', type: 'goal', label: 'GOAL! DeBrusk', sequence: 6, period: 2, timestamp: 1560, players: ['DeBrusk'], zone: 'offensive', outcome: 'success', thematicGroups: ['goals'] },
        { id: 'bos-p3', type: 'period', label: 'Period 3', sequence: 7, period: 3, timestamp: 2400, thematicGroups: ['periods'] },
        { id: 'bos-goal-4', type: 'goal', label: 'GOAL! Bergeron', sequence: 8, period: 3, timestamp: 2680, players: ['Bergeron'], zone: 'offensive', outcome: 'success', thematicGroups: ['goals'] },
        { id: 'bos-goal-nyr', type: 'goal', label: 'GOAL! Zibanejad (NYR)', sequence: 9, period: 3, timestamp: 2950, players: ['Zibanejad'], zone: 'offensive', outcome: 'success', thematicGroups: ['goals'] },
      ]
    }
  ]


  useEffect(() => {
    if (!containerRef.current) return

    const container = containerRef.current
    const scene = sceneRef.current

    // Clean up previous scene
    if (scene.animationId) {
      cancelAnimationFrame(scene.animationId)
    }
    if (scene.controls) {
      scene.controls.dispose()
    }
    if (scene.renderer && container.contains(scene.renderer.domElement)) {
      container.removeChild(scene.renderer.domElement)
    }

    // Constants - compact space for very close neural network positioning
    const maxParticleCount = 1000
    const particleCount = 500
    const r = 1200
    const rHalf = r / 2
    const minDistance = 100

    // Initialize advanced scene with physics and post-processing
    scene.scene = new THREE.Scene()

    // Enhanced camera with better field of view for immersive experience
    scene.camera = new THREE.PerspectiveCamera(60, container.clientWidth / container.clientHeight, 0.1, 5000)
    scene.camera.position.set(0, 0, 1000)

    // Advanced renderer with enhanced capabilities
    scene.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
      stencil: false,
      depth: true
    })
    scene.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    scene.renderer.setSize(container.clientWidth, container.clientHeight)
    scene.renderer.setClearColor(0x000000, 0) // Pure black background for military theme
    scene.renderer.shadowMap.enabled = true
    scene.renderer.shadowMap.type = THREE.PCFSoftShadowMap
    scene.renderer.domElement.style.position = 'absolute'
    scene.renderer.domElement.style.top = '0'
    scene.renderer.domElement.style.left = '0'
    scene.renderer.domElement.style.width = '100%'
    scene.renderer.domElement.style.height = '100%'
    container.appendChild(scene.renderer.domElement)

    // Initialize CANNON.js physics world
    scene.physicsWorld = new CANNON.World()
    scene.physicsWorld.gravity.set(0, 0, 0) // Zero gravity for floating neural network
    scene.physicsWorld.broadphase = new CANNON.SAPBroadphase(scene.physicsWorld)
    scene.physicsWorld.allowSleep = true

    // Physics material for neural network interactions
    const physicsMaterial = new CANNON.Material({ friction: 0.1, restitution: 0.8 })
    scene.physicsWorld.addContactMaterial(new CANNON.ContactMaterial(physicsMaterial, physicsMaterial, {
      friction: 0.1,
      restitution: 0.3
    }))

    // Post-processing composer for futuristic effects
    scene.composer = new EffectComposer(scene.renderer)
    scene.composer.addPass(new RenderPass(scene.scene, scene.camera))

    // Add bloom effect for glowing particles
    const bloomPass = new UnrealBloomPass(
      new THREE.Vector2(container.clientWidth, container.clientHeight),
      1.5, // strength
      0.4, // radius
      0.85 // threshold
    )
    scene.composer.addPass(bloomPass)

    // Add dynamic lighting for military theme atmosphere
    const ambientLight = new THREE.AmbientLight(0x111111, 0.3)
    scene.scene.add(ambientLight)

    const directionalLight = new THREE.DirectionalLight(0x666666, 0.8)
    directionalLight.position.set(1000, 1000, 1000)
    directionalLight.castShadow = true
    directionalLight.shadow.mapSize.width = 2048
    directionalLight.shadow.mapSize.height = 2048
    scene.scene.add(directionalLight)

    // Add point lights for energy field effects
    const pointLight1 = new THREE.PointLight(0xff0044, 0.5, 2000)
    pointLight1.position.set(-500, 500, -500)
    scene.scene.add(pointLight1)

    const pointLight2 = new THREE.PointLight(0x333333, 0.5, 2000)
    pointLight2.position.set(500, -500, 500)
    scene.scene.add(pointLight2)

    // Add orbit controls
    scene.controls = new SimpleOrbitControls(scene.camera, scene.renderer.domElement)
    console.log('OrbitControls initialized')

    // Create advanced particle system with custom shaders
    scene.particlePositions = new Float32Array(maxParticleCount * 3)
    scene.positions = new Float32Array(maxParticleCount * maxParticleCount * 3)
    scene.colors = new Float32Array(maxParticleCount * maxParticleCount * 3)

    // Advanced particle geometry with custom attributes
    scene.particles = new THREE.BufferGeometry()
    scene.particles.setAttribute('position', new THREE.BufferAttribute(scene.particlePositions, 3))
    scene.particles.setAttribute('size', new THREE.BufferAttribute(new Float32Array(maxParticleCount), 1))
    scene.particles.setAttribute('color', new THREE.BufferAttribute(new Float32Array(maxParticleCount * 3), 3))
    scene.particles.setAttribute('energy', new THREE.BufferAttribute(new Float32Array(maxParticleCount), 1))
    scene.particles.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(maxParticleCount), 1))

    // Custom shader material for futuristic particles
    scene.particleMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 },
        pixelRatio: { value: Math.min(window.devicePixelRatio, 2) }
      },
      vertexShader: ParticleVertexShader,
      fragmentShader: ParticleFragmentShader,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true
    })

    // Create point cloud with custom material
    scene.pointCloud = new THREE.Points(scene.particles, scene.particleMaterial)
    scene.scene.add(scene.pointCloud)

    // Initialize particle data with enhanced properties
    scene.particlesData = []

    // Create trails geometry for motion blur effects
    scene.trailsGeometry = new THREE.BufferGeometry()
    const trailPositions = new Float32Array(maxParticleCount * 20 * 3) // 20 trail points per particle
    scene.trailsGeometry.setAttribute('position', new THREE.BufferAttribute(trailPositions, 3))
    scene.trailsGeometry.setAttribute('color', new THREE.BufferAttribute(new Float32Array(maxParticleCount * 20 * 3), 3))
    scene.trailsGeometry.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(maxParticleCount * 20), 1))

    // Trails material with energy flow effect
    scene.connectionMaterial = new THREE.ShaderMaterial({
      uniforms: {
        time: { value: 0 }
      },
      vertexShader: ConnectionVertexShader,
      fragmentShader: ConnectionFragmentShader,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      vertexColors: true
    })

    scene.trailsMesh = new THREE.LineSegments(scene.trailsGeometry, scene.connectionMaterial)
    scene.scene.add(scene.trailsMesh)

    // Default games data with player-centric neural networks
    const defaultGames: GameData[] = [
      {
        id: 'mtl-tor-2024-01-15',
        homeTeam: 'MTL',
        awayTeam: 'TOR',
        homeScore: 3,
        awayScore: 2,
        date: '2024-01-15',
        homeRoster: [
          { id: 'mtl-14', name: 'Nick Suzuki', team: 'home', jerseyNumber: '14', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-22', name: 'Cole Caufield', team: 'home', jerseyNumber: '22', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'mtl-77', name: 'Kirby Dach', team: 'home', jerseyNumber: '77', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-20', name: 'Juraj Slafkovsky', team: 'home', jerseyNumber: '20', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'mtl-17', name: 'Josh Anderson', team: 'home', jerseyNumber: '17', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'mtl-71', name: 'Jake Evans', team: 'home', jerseyNumber: '71', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-11', name: 'Brendan Gallagher', team: 'home', jerseyNumber: '11', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'mtl-40', name: 'Joel Armia', team: 'home', jerseyNumber: '40', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'mtl-28', name: 'Christian Dvorak', team: 'home', jerseyNumber: '28', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-49', name: 'Rafael Harvey-Pinard', team: 'home', jerseyNumber: '49', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'mtl-60', name: 'Alex Newhook', team: 'home', jerseyNumber: '60', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-58', name: 'Nathan Légaré', team: 'home', jerseyNumber: '58', position: 'C', connections: [], interactionCount: 0 },
          { id: 'mtl-8', name: 'Michael Matheson', team: 'home', jerseyNumber: '8', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-26', name: 'Johnathan Kovacevic', team: 'home', jerseyNumber: '26', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-72', name: 'Tanner Pearson', team: 'home', jerseyNumber: '72', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'mtl-75', name: 'Arber Xhekaj', team: 'home', jerseyNumber: '75', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-52', name: 'Justin Barron', team: 'home', jerseyNumber: '52', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-73', name: 'Brett Kulak', team: 'home', jerseyNumber: '73', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-44', name: 'Jayden Struble', team: 'home', jerseyNumber: '44', position: 'D', connections: [], interactionCount: 0 },
          { id: 'mtl-35', name: 'Cayden Primeau', team: 'home', jerseyNumber: '35', position: 'G', connections: [], interactionCount: 0 }
        ],
        awayRoster: [
          { id: 'tor-34', name: 'Auston Matthews', team: 'away', jerseyNumber: '34', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-16', name: 'Mitch Marner', team: 'away', jerseyNumber: '16', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'tor-91', name: 'John Tavares', team: 'away', jerseyNumber: '91', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-88', name: 'William Nylander', team: 'away', jerseyNumber: '88', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'tor-89', name: 'Nicholas Robertson', team: 'away', jerseyNumber: '89', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'tor-47', name: 'Leo Carlsson', team: 'away', jerseyNumber: '47', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-73', name: 'Pontus Holmberg', team: 'away', jerseyNumber: '73', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'tor-25', name: 'Max Domi', team: 'away', jerseyNumber: '25', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-36', name: 'Bobby McMann', team: 'away', jerseyNumber: '36', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-15', name: 'Alexander Kerfoot', team: 'away', jerseyNumber: '15', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-44', name: 'Morgan Rielly', team: 'away', jerseyNumber: '44', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-8', name: 'TJ Brodie', team: 'away', jerseyNumber: '8', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-26', name: 'Rasmus Sandin', team: 'away', jerseyNumber: '26', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-3', name: 'Justin Holl', team: 'away', jerseyNumber: '3', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-18', name: 'Jake McCabe', team: 'away', jerseyNumber: '18', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-28', name: 'Ben Harpur', team: 'away', jerseyNumber: '28', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-23', name: 'Travis Dermott', team: 'away', jerseyNumber: '23', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-64', name: 'David Kampf', team: 'away', jerseyNumber: '64', position: 'C', connections: [], interactionCount: 0 },
          { id: 'tor-78', name: 'TJ Brodie', team: 'away', jerseyNumber: '78', position: 'D', connections: [], interactionCount: 0 },
          { id: 'tor-60', name: 'Joseph Woll', team: 'away', jerseyNumber: '60', position: 'G', connections: [], interactionCount: 0 }
        ],
        events: [
          // ===== PERIOD 1: HIGH-INTENSITY START =====

          // Opening faceoff - creates initial connection between centers
          { id: 'p1-faceoff', type: 'faceoff', label: 'FO', sequence: 1, period: 1, timestamp: 0, players: ['mtl-14', 'tor-34'], zone: 'neutral', outcome: 'success' },

          // MONTREAL'S OPENING RUSH - Pass chain connecting Suzuki → Caufield → Shot → Save
          { id: 'mtl-rush-1', type: 'pass', label: 'P', sequence: 2, period: 1, timestamp: 2, players: ['mtl-14', 'mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['p1-faceoff'] },
          { id: 'mtl-shot-1', type: 'shot', label: 'S', sequence: 3, period: 1, timestamp: 4, players: ['mtl-22'], zone: 'offensive', outcome: 'failure', relatedEvents: ['mtl-rush-1'] },
          { id: 'tor-save-1', type: 'save', label: 'SV', sequence: 4, period: 1, timestamp: 5, players: ['tor-60'], zone: 'defensive', outcome: 'success', relatedEvents: ['mtl-shot-1'] },

          // TORONTO COUNTER-ATTACK - Clear → Pass chain → Shot → Save (defensive web)
          { id: 'tor-clear-1', type: 'pass', label: 'CLR', sequence: 5, period: 1, timestamp: 10, players: ['tor-44'], zone: 'defensive', outcome: 'success' },
          { id: 'tor-break-1', type: 'pass', label: 'P', sequence: 6, period: 1, timestamp: 12, players: ['tor-34', 'tor-16'], zone: 'neutral', outcome: 'success', relatedEvents: ['tor-clear-1'] },
          { id: 'tor-shot-1', type: 'shot', label: 'S', sequence: 7, period: 1, timestamp: 14, players: ['tor-16'], zone: 'offensive', outcome: 'failure', relatedEvents: ['tor-break-1'] },
          { id: 'mtl-save-1', type: 'save', label: 'SV', sequence: 8, period: 1, timestamp: 15, players: ['mtl-35'], zone: 'defensive', outcome: 'success', relatedEvents: ['tor-shot-1'] },

          // PHYSICAL PLAY SEQUENCE - Hit creates takeaway creates scoring chance
          { id: 'mtl-hit-1', type: 'hit', label: 'HIT', sequence: 9, period: 1, timestamp: 30, players: ['mtl-75', 'tor-16'], zone: 'neutral', outcome: 'success' },
          { id: 'tor-takeaway-1', type: 'takeaway', label: 'TK', sequence: 10, period: 1, timestamp: 32, players: ['tor-88'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-hit-1'] },
          { id: 'tor-pass-1', type: 'pass', label: 'P', sequence: 11, period: 1, timestamp: 34, players: ['tor-88', 'tor-34'], zone: 'offensive', outcome: 'success', relatedEvents: ['tor-takeaway-1'] },
          { id: 'tor-shot-2', type: 'shot', label: 'S', sequence: 12, period: 1, timestamp: 36, players: ['tor-34'], zone: 'offensive', outcome: 'failure', relatedEvents: ['tor-pass-1'] },
          { id: 'mtl-save-2', type: 'save', label: 'SV', sequence: 13, period: 1, timestamp: 37, players: ['mtl-35'], zone: 'defensive', outcome: 'success', relatedEvents: ['tor-shot-2'] },

          // MONTREAL POWERPLAY GOAL - Complex 3-player connection: Matheson → Suzuki → Caufield → GOAL
          { id: 'mtl-pp-blue', type: 'pass', label: 'P', sequence: 14, period: 1, timestamp: 125, players: ['mtl-8', 'mtl-14'], zone: 'offensive', outcome: 'success' },
          { id: 'mtl-pp-one-timer', type: 'pass', label: 'P', sequence: 15, period: 1, timestamp: 127, players: ['mtl-14', 'mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-pp-blue'] },
          { id: 'mtl-goal-shot-pp', type: 'shot', label: 'S', sequence: 16, period: 1, timestamp: 129, players: ['mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-pp-one-timer'] },
          { id: 'mtl-goal-1', type: 'goal', label: 'GOAL', sequence: 17, period: 1, timestamp: 130, players: ['mtl-22', 'mtl-14', 'mtl-8'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-goal-shot-pp', 'mtl-pp-one-timer', 'mtl-pp-blue'] },

          // ===== PERIOD 2: DEFENSIVE BATTLES =====

          // DEFENSIVE STANDOUT - Matheson block creates transition opportunity
          { id: 'p2-faceoff', type: 'faceoff', label: 'FO', sequence: 18, period: 2, timestamp: 1200, players: ['mtl-71', 'tor-91'], zone: 'neutral', outcome: 'success' },
          { id: 'tor-offensive-push', type: 'pass', label: 'P', sequence: 19, period: 2, timestamp: 1202, players: ['tor-91', 'tor-88'], zone: 'offensive', outcome: 'success', relatedEvents: ['p2-faceoff'] },
          { id: 'mtl-block-1', type: 'block', label: 'BLK', sequence: 20, period: 2, timestamp: 1204, players: ['mtl-8', 'tor-88'], zone: 'defensive', outcome: 'success', relatedEvents: ['tor-offensive-push'] },
          { id: 'mtl-transition-1', type: 'pass', label: 'P', sequence: 21, period: 2, timestamp: 1206, players: ['mtl-8', 'mtl-26'], zone: 'defensive', outcome: 'success', relatedEvents: ['mtl-block-1'] },
          { id: 'mtl-transition-2', type: 'pass', label: 'P', sequence: 22, period: 2, timestamp: 1208, players: ['mtl-26', 'mtl-77'], zone: 'neutral', outcome: 'success', relatedEvents: ['mtl-transition-1'] },
          { id: 'mtl-transition-3', type: 'pass', label: 'P', sequence: 23, period: 2, timestamp: 1210, players: ['mtl-77', 'mtl-20'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-transition-2'] },
          { id: 'mtl-breakaway-shot', type: 'shot', label: 'S', sequence: 24, period: 2, timestamp: 1212, players: ['mtl-20'], zone: 'offensive', outcome: 'failure', relatedEvents: ['mtl-transition-3'] },
          { id: 'tor-save-defensive', type: 'save', label: 'SV', sequence: 25, period: 2, timestamp: 1213, players: ['tor-60'], zone: 'defensive', outcome: 'success', relatedEvents: ['mtl-breakaway-shot'] },

          // TORONTO POWERPLAY RESPONSE - 3-player passing sequence leading to goal
          { id: 'tor-pp-faceoff', type: 'faceoff', label: 'FO', sequence: 26, period: 2, timestamp: 1300, players: ['mtl-71', 'tor-91'], zone: 'neutral', outcome: 'success' },
          { id: 'tor-pp-pass-1', type: 'pass', label: 'P', sequence: 27, period: 2, timestamp: 1302, players: ['tor-91', 'tor-88'], zone: 'offensive', outcome: 'success', relatedEvents: ['tor-pp-faceoff'] },
          { id: 'tor-pp-pass-2', type: 'pass', label: 'P', sequence: 28, period: 2, timestamp: 1304, players: ['tor-88', 'tor-16'], zone: 'offensive', outcome: 'success', relatedEvents: ['tor-pp-pass-1'] },
          { id: 'tor-pp-goal-shot', type: 'shot', label: 'S', sequence: 29, period: 2, timestamp: 1306, players: ['tor-16'], zone: 'offensive', outcome: 'success', relatedEvents: ['tor-pp-pass-2'] },
          { id: 'tor-goal-2', type: 'goal', label: 'GOAL', sequence: 30, period: 2, timestamp: 1307, players: ['tor-16', 'tor-88', 'tor-91'], zone: 'offensive', outcome: 'success', relatedEvents: ['tor-pp-goal-shot', 'tor-pp-pass-2', 'tor-pp-pass-1'] },

          // ===== PERIOD 3: DRAMATIC FINISH =====

          // MONTREAL'S COMEBACK - Complex passing sequence through multiple players
          { id: 'p3-faceoff-final', type: 'faceoff', label: 'FO', sequence: 31, period: 3, timestamp: 2400, players: ['mtl-14', 'tor-34'], zone: 'neutral', outcome: 'success' },
          { id: 'mtl-final-push-1', type: 'pass', label: 'P', sequence: 32, period: 3, timestamp: 2402, players: ['mtl-14', 'mtl-17'], zone: 'offensive', outcome: 'success', relatedEvents: ['p3-faceoff-final'] },
          { id: 'mtl-final-push-2', type: 'pass', label: 'P', sequence: 33, period: 3, timestamp: 2404, players: ['mtl-17', 'mtl-40'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-final-push-1'] },
          { id: 'mtl-final-push-3', type: 'pass', label: 'P', sequence: 34, period: 3, timestamp: 2406, players: ['mtl-40', 'mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-final-push-2'] },
          { id: 'mtl-game-winner-shot', type: 'shot', label: 'S', sequence: 35, period: 3, timestamp: 2408, players: ['mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-final-push-3'] },
          { id: 'mtl-goal-3', type: 'goal', label: 'GOAL', sequence: 36, period: 3, timestamp: 2409, players: ['mtl-22', 'mtl-40', 'mtl-17', 'mtl-14'], zone: 'offensive', outcome: 'success', relatedEvents: ['mtl-game-winner-shot', 'mtl-final-push-3', 'mtl-final-push-2', 'mtl-final-push-1'] },

          // PENALTY SEQUENCE - Physical play leading to powerplay
          { id: 'late-game-hit', type: 'hit', label: 'HIT', sequence: 37, period: 3, timestamp: 2500, players: ['mtl-75', 'tor-16'], zone: 'neutral', outcome: 'failure' },
          { id: 'penalty-call', type: 'penalty', label: 'PEN', sequence: 38, period: 3, timestamp: 2501, players: ['mtl-75'], zone: 'neutral', outcome: 'failure', relatedEvents: ['late-game-hit'] },

          // POWERPLAY DEFENSE - Toronto PP vs Montreal PK
          { id: 'pp-faceoff', type: 'faceoff', label: 'FO', sequence: 39, period: 3, timestamp: 2510, players: ['mtl-28', 'tor-34'], zone: 'defensive', outcome: 'success' },
          { id: 'tor-pp-shot-1', type: 'shot', label: 'S', sequence: 40, period: 3, timestamp: 2512, players: ['tor-34'], zone: 'offensive', outcome: 'failure', relatedEvents: ['pp-faceoff'] },
          { id: 'mtl-block-pp', type: 'block', label: 'BLK', sequence: 41, period: 3, timestamp: 2513, players: ['mtl-8'], zone: 'defensive', outcome: 'success', relatedEvents: ['tor-pp-shot-1'] },
          { id: 'mtl-pk-clear', type: 'pass', label: 'CLR', sequence: 42, period: 3, timestamp: 2515, players: ['mtl-26'], zone: 'defensive', outcome: 'success', relatedEvents: ['mtl-block-pp'] },

          // EMPTY NET SEQUENCE - Final dramatic moments
          { id: 'empty-net-1', type: 'pass', label: 'P', sequence: 43, period: 3, timestamp: 2970, players: ['mtl-11', 'mtl-49'], zone: 'offensive', outcome: 'success' },
          { id: 'empty-net-2', type: 'pass', label: 'P', sequence: 44, period: 3, timestamp: 2972, players: ['mtl-49', 'mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['empty-net-1'] },
          { id: 'empty-net-goal-shot', type: 'shot', label: 'S', sequence: 45, period: 3, timestamp: 2974, players: ['mtl-22'], zone: 'offensive', outcome: 'success', relatedEvents: ['empty-net-2'] },
          { id: 'mtl-insurance-goal', type: 'goal', label: 'GOAL', sequence: 46, period: 3, timestamp: 2975, players: ['mtl-22', 'mtl-49', 'mtl-11'], zone: 'offensive', outcome: 'success', relatedEvents: ['empty-net-goal-shot', 'empty-net-2', 'empty-net-1'] }
        ]
      },
      {
        id: 'bos-nyr-2024-01-16',
        homeTeam: 'BOS',
        awayTeam: 'NYR',
        homeScore: 4,
        awayScore: 1,
        date: '2024-01-16',
        homeRoster: [
          { id: 'bos-63', name: 'Brad Marchand', team: 'home', jerseyNumber: '63', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'bos-88', name: 'David Pastrnak', team: 'home', jerseyNumber: '88', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'bos-73', name: 'Charlie McAvoy', team: 'home', jerseyNumber: '73', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-37', name: 'Pavel Zacha', team: 'home', jerseyNumber: '37', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-13', name: 'Charlie Coyle', team: 'home', jerseyNumber: '13', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-74', name: 'Jake DeBrusk', team: 'home', jerseyNumber: '74', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'bos-25', name: 'Brandon Carlo', team: 'home', jerseyNumber: '25', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-75', name: 'Trent Frederic', team: 'home', jerseyNumber: '75', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-48', name: 'Morgan Geekie', team: 'home', jerseyNumber: '48', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-54', name: 'Matt Grzelcyk', team: 'home', jerseyNumber: '54', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-86', name: 'Kevin Shattenkirk', team: 'home', jerseyNumber: '86', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-46', name: 'David Krejci', team: 'home', jerseyNumber: '46', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-41', name: 'Patrice Bergeron', team: 'home', jerseyNumber: '41', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-28', name: 'James van Riemsdyk', team: 'home', jerseyNumber: '28', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'bos-27', name: 'Hampus Lindholm', team: 'home', jerseyNumber: '27', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-52', name: 'Craig Smith', team: 'home', jerseyNumber: '52', position: 'C', connections: [], interactionCount: 0 },
          { id: 'bos-62', name: 'Parker Wotherspoon', team: 'home', jerseyNumber: '62', position: 'D', connections: [], interactionCount: 0 },
          { id: 'bos-77', name: 'A.J. Greer', team: 'home', jerseyNumber: '77', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'bos-60', name: 'Justin Brazeau', team: 'home', jerseyNumber: '60', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'bos-1', name: 'Jeremy Swayman', team: 'home', jerseyNumber: '1', position: 'G', connections: [], interactionCount: 0 }
        ],
        awayRoster: [
          { id: 'nyr-93', name: 'Mika Zibanejad', team: 'away', jerseyNumber: '93', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-20', name: 'Chris Kreider', team: 'away', jerseyNumber: '20', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'nyr-16', name: 'Ryan Strome', team: 'away', jerseyNumber: '16', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-26', name: 'Kaapo Kakko', team: 'away', jerseyNumber: '26', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'nyr-42', name: 'Alexis Lafreniere', team: 'away', jerseyNumber: '42', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'nyr-21', name: 'Filip Chytil', team: 'away', jerseyNumber: '21', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-6', name: 'Vladimir Tarasenko', team: 'away', jerseyNumber: '6', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'nyr-40', name: 'Will Cuylle', team: 'away', jerseyNumber: '40', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'nyr-17', name: 'Barclay Goodrow', team: 'away', jerseyNumber: '17', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-13', name: 'Matt Rempe', team: 'away', jerseyNumber: '13', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-4', name: 'Adam Fox', team: 'away', jerseyNumber: '4', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-76', name: 'Jacob Trouba', team: 'away', jerseyNumber: '76', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-79', name: 'K\'Andre Miller', team: 'away', jerseyNumber: '79', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-5', name: 'Braden Schneider', team: 'away', jerseyNumber: '5', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-36', name: 'Zac Jones', team: 'away', jerseyNumber: '36', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-18', name: 'Jake Leschyshyn', team: 'away', jerseyNumber: '18', position: 'C', connections: [], interactionCount: 0 },
          { id: 'nyr-23', name: 'Adam Edstrom', team: 'away', jerseyNumber: '23', position: 'RW', connections: [], interactionCount: 0 },
          { id: 'nyr-43', name: 'Jimmy Vesey', team: 'away', jerseyNumber: '43', position: 'LW', connections: [], interactionCount: 0 },
          { id: 'nyr-24', name: 'Kaapo Kakko', team: 'away', jerseyNumber: '24', position: 'D', connections: [], interactionCount: 0 },
          { id: 'nyr-30', name: 'Igor Shesterkin', team: 'away', jerseyNumber: '30', position: 'G', connections: [], interactionCount: 0 }
        ],
        events: [
          // ===== PERIOD 1: BRUINS DOMINANCE =====

          // Opening faceoff battle - Zacha vs Zibanejad
          { id: 'p1-faceoff', type: 'faceoff', label: 'FO', sequence: 1, period: 1, timestamp: 0, players: ['bos-37', 'nyr-93'], zone: 'neutral', outcome: 'success' },

          // BOSTON'S LIGHTNING-FAST ATTACK - Zacha → Pastrnak → Marchand → GOAL
          { id: 'bos-attack-1', type: 'pass', label: 'P', sequence: 2, period: 1, timestamp: 2, players: ['bos-37', 'bos-88'], zone: 'offensive', outcome: 'success', relatedEvents: ['p1-faceoff'] },
          { id: 'bos-attack-2', type: 'pass', label: 'P', sequence: 3, period: 1, timestamp: 4, players: ['bos-88', 'bos-63'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-attack-1'] },
          { id: 'bos-goal-shot-1', type: 'shot', label: 'S', sequence: 4, period: 1, timestamp: 6, players: ['bos-63'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-attack-2'] },
          { id: 'bos-goal-1', type: 'goal', label: 'GOAL', sequence: 5, period: 1, timestamp: 7, players: ['bos-63', 'bos-88', 'bos-37'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-goal-shot-1', 'bos-attack-2', 'bos-attack-1'] },

          // RANGERS RESPONSE - Defensive clear creates transition
          { id: 'nyr-defensive-clear', type: 'pass', label: 'CLR', sequence: 6, period: 1, timestamp: 20, players: ['nyr-4'], zone: 'defensive', outcome: 'success' },
          { id: 'nyr-transition-1', type: 'pass', label: 'P', sequence: 7, period: 1, timestamp: 22, players: ['nyr-93', 'nyr-20'], zone: 'neutral', outcome: 'success', relatedEvents: ['nyr-defensive-clear'] },
          { id: 'nyr-transition-2', type: 'pass', label: 'P', sequence: 8, period: 1, timestamp: 24, players: ['nyr-20', 'nyr-26'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-transition-1'] },
          { id: 'nyr-shot-1', type: 'shot', label: 'S', sequence: 9, period: 1, timestamp: 26, players: ['nyr-26'], zone: 'offensive', outcome: 'failure', relatedEvents: ['nyr-transition-2'] },
          { id: 'bos-save-1', type: 'save', label: 'SV', sequence: 10, period: 1, timestamp: 27, players: ['bos-1'], zone: 'defensive', outcome: 'success', relatedEvents: ['nyr-shot-1'] },

          // PHYSICAL SEQUENCE - McAvoy hits Kreider, creates takeaway chance
          { id: 'bos-physical-hit', type: 'hit', label: 'HIT', sequence: 11, period: 1, timestamp: 45, players: ['bos-73', 'nyr-20'], zone: 'neutral', outcome: 'success' },
          { id: 'nyr-takeaway-chance', type: 'takeaway', label: 'TK', sequence: 12, period: 1, timestamp: 47, players: ['nyr-16'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-physical-hit'] },
          { id: 'nyr-scoring-chance', type: 'pass', label: 'P', sequence: 13, period: 1, timestamp: 49, players: ['nyr-16', 'nyr-93'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-takeaway-chance'] },
          { id: 'nyr-missed-chance', type: 'shot', label: 'S', sequence: 14, period: 1, timestamp: 51, players: ['nyr-93'], zone: 'offensive', outcome: 'failure', relatedEvents: ['nyr-scoring-chance'] },
          { id: 'bos-save-2', type: 'save', label: 'SV', sequence: 15, period: 1, timestamp: 52, players: ['bos-1'], zone: 'defensive', outcome: 'success', relatedEvents: ['nyr-missed-chance'] },

          // ===== PERIOD 2: BRUINS CONTINUE DOMINANCE =====

          // DEFENSIVE MASTERCLASS - Trouba blocks Pastrnak, Bruins rebound for goal
          { id: 'p2-faceoff', type: 'faceoff', label: 'FO', sequence: 16, period: 2, timestamp: 1200, players: ['bos-13', 'nyr-16'], zone: 'neutral', outcome: 'success' },
          { id: 'bos-defensive-setup', type: 'pass', label: 'P', sequence: 17, period: 2, timestamp: 1202, players: ['bos-13', 'bos-73'], zone: 'offensive', outcome: 'success', relatedEvents: ['p2-faceoff'] },
          { id: 'bos-offensive-play', type: 'pass', label: 'P', sequence: 18, period: 2, timestamp: 1204, players: ['bos-73', 'bos-88'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-defensive-setup'] },
          { id: 'nyr-defensive-block', type: 'block', label: 'BLK', sequence: 19, period: 2, timestamp: 1206, players: ['nyr-76', 'bos-88'], zone: 'defensive', outcome: 'success', relatedEvents: ['bos-offensive-play'] },
          { id: 'bos-rebound-offense', type: 'pass', label: 'P', sequence: 20, period: 2, timestamp: 1208, players: ['bos-74'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-defensive-block'] },
          { id: 'bos-rebound-shot', type: 'shot', label: 'S', sequence: 21, period: 2, timestamp: 1210, players: ['bos-74'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-rebound-offense'] },
          { id: 'bos-goal-2', type: 'goal', label: 'GOAL', sequence: 22, period: 2, timestamp: 1211, players: ['bos-74', 'bos-88', 'bos-73', 'bos-13'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-rebound-shot', 'bos-rebound-offense', 'nyr-defensive-block'] },

          // ===== PERIOD 3: RANGERS FIGHT BACK =====

          // RANGERS POWERPLAY SUCCESS - 3-player passing sequence
          { id: 'p3-faceoff', type: 'faceoff', label: 'FO', sequence: 23, period: 3, timestamp: 2400, players: ['bos-37', 'nyr-93'], zone: 'neutral', outcome: 'success' },
          { id: 'nyr-pp-play-1', type: 'pass', label: 'P', sequence: 24, period: 3, timestamp: 2402, players: ['nyr-93', 'nyr-26'], zone: 'offensive', outcome: 'success', relatedEvents: ['p3-faceoff'] },
          { id: 'nyr-pp-play-2', type: 'pass', label: 'P', sequence: 25, period: 3, timestamp: 2404, players: ['nyr-26', 'nyr-20'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-pp-play-1'] },
          { id: 'nyr-pp-goal-shot', type: 'shot', label: 'S', sequence: 26, period: 3, timestamp: 2406, players: ['nyr-20'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-pp-play-2'] },
          { id: 'nyr-goal-1', type: 'goal', label: 'GOAL', sequence: 27, period: 3, timestamp: 2407, players: ['nyr-20', 'nyr-26', 'nyr-93'], zone: 'offensive', outcome: 'success', relatedEvents: ['nyr-pp-goal-shot', 'nyr-pp-play-2', 'nyr-pp-play-1'] },

          // BRUINS CLINCH IT - Empty net goal seals victory
          { id: 'bos-empty-net-1', type: 'pass', label: 'P', sequence: 28, period: 3, timestamp: 2970, players: ['bos-46', 'bos-41'], zone: 'offensive', outcome: 'success' },
          { id: 'bos-empty-net-shot', type: 'shot', label: 'S', sequence: 29, period: 3, timestamp: 2972, players: ['bos-41'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-empty-net-1'] },
          { id: 'bos-goal-3', type: 'goal', label: 'GOAL', sequence: 30, period: 3, timestamp: 2973, players: ['bos-41', 'bos-46'], zone: 'offensive', outcome: 'success', relatedEvents: ['bos-empty-net-shot', 'bos-empty-net-1'] }
        ]
      }
    ]

    const allGames = games || defaultGames

    // Game cluster positions - arrange games in a very close circular pattern for ultra-easy navigation
    const getGameClusterCenter = (gameIndex: number, totalGames: number): THREE.Vector3 => {
      const angle = (gameIndex / totalGames) * Math.PI * 2
      const radius = 300 // Much closer distance from center for each game cluster
      const height = (gameIndex % 2) * 150 - 75 // Minimal height variation for maximum proximity

      return new THREE.Vector3(
        Math.cos(angle) * radius,
        height,
        Math.sin(angle) * radius
      )
    }


    // Calculate cluster positions for thematic grouping within each game
    const calculateClusterPosition = (event: GameEvent, gameIndex: number, totalGames: number): THREE.Vector3 => {
      const gameCenter = getGameClusterCenter(gameIndex, totalGames)

      // Base clusters relative to game center - scaled down for each game's neural network
      const clusters = {
        periods: new THREE.Vector3(0, 200, 0),
        goals: new THREE.Vector3(250, 0, 0),
        shots: new THREE.Vector3(180, 0, 120),
        passes: new THREE.Vector3(120, 0, 200),
        saves: new THREE.Vector3(-180, 0, 120),
        hits: new THREE.Vector3(-250, 0, 0),
        penalties: new THREE.Vector3(-180, 0, -120),
        players: new THREE.Vector3(0, -250, 0),
        faceoffs: new THREE.Vector3(0, 150, 300),
        takeaways: new THREE.Vector3(-120, 0, 200),
        rebounds: new THREE.Vector3(180, 0, -120),
        blocks: new THREE.Vector3(120, 0, -200)
      }

      let basePosition = gameCenter.clone()

      // Primary cluster based on event type
      if (clusters[event.type as keyof typeof clusters]) {
        const clusterOffset = clusters[event.type as keyof typeof clusters].clone()
        basePosition.add(clusterOffset)
      }

      // Adjust for period (depth layers) - increased separation
      const periodOffset = ((event.period || 1) - 1) * 150
      basePosition.y += periodOffset

      // Add significant randomness within cluster for neural network scattering
      const spread = 120
      basePosition.x += (Math.random() - 0.5) * spread
      basePosition.y += (Math.random() - 0.5) * spread * 0.5
      basePosition.z += (Math.random() - 0.5) * spread

      // Thematic adjustments
      if (event.thematicGroups?.includes('powerplay-goals')) {
        basePosition.x += 30
        basePosition.z += 30
      }
      if (event.thematicGroups?.includes('penalty-kills')) {
        basePosition.x -= 30
        basePosition.z += 30
      }

      return basePosition
    }

    // Initialize particles with ALL PLAYERS from both teams across the environment
    let particleIndex = 0

    // Process each game and create player particles for its neural network
    allGames.forEach((game, gameIndex) => {
      const gameCenter = getGameClusterCenter(gameIndex, allGames.length)

      // Create particles for home team players (20 players, red particles)
      game.homeRoster.slice(0, 20).forEach((player, playerIndex) => {
        if (particleIndex >= maxParticleCount) return

      const particleData: ParticleData = {
          id: player.id,
          position: new THREE.Vector3(),
        velocity: new THREE.Vector3(
            -0.005 + Math.random() * 0.01,
            -0.005 + Math.random() * 0.01,
            -0.005 + Math.random() * 0.01
          ),
          size: 4, // Larger particles for players
          color: { r: 0.8, g: 0.2, b: 0.2 }, // Red for home team
          playerId: player.id,
          team: 'home',
          jerseyNumber: player.jerseyNumber,
          name: player.name,
          connections: [],
          clusterPosition: new THREE.Vector3(),
          gameId: game.id,
          numConnections: 0,
          energy: 0.5 + Math.random() * 0.5, // Dynamic energy level
          trail: [] // Initialize trail array
      }

        // Position players in a sphere around the game center
        const angle = (playerIndex / 20) * Math.PI * 2
        const radius = 120 + Math.random() * 60 // Increased radius for better spacing
        const heightOffset = (playerIndex % 4 - 2) * 40 // Increased height spread for better separation

        const x = gameCenter.x + Math.cos(angle) * radius
        const y = gameCenter.y + heightOffset
        const z = gameCenter.z + Math.sin(angle) * radius

      // Create physics body for realistic interactions
      const physicsShape = new CANNON.Sphere(2)
      particleData.physicsBody = new CANNON.Body({
        mass: 1,
        position: new CANNON.Vec3(x, y, z),
        velocity: new CANNON.Vec3(
          particleData.velocity.x * 100,
          particleData.velocity.y * 100,
          particleData.velocity.z * 100
        ),
        material: new CANNON.Material({ friction: 0.1, restitution: 0.8 })
      })
      particleData.physicsBody.addShape(physicsShape)
      scene.physicsWorld!.addBody(particleData.physicsBody)

        particleData.position.set(x, y, z)
        particleData.clusterPosition.copy(particleData.position)

        // Set shader attributes for the particle
        if (!scene.particles) return
        const positions = scene.particles.attributes.position.array as Float32Array
        const colors = scene.particles.attributes.color.array as Float32Array
        const sizes = scene.particles.attributes.size.array as Float32Array
        const energies = scene.particles.attributes.energy.array as Float32Array
        const alphas = scene.particles.attributes.alpha.array as Float32Array

        positions[particleIndex * 3] = x
        positions[particleIndex * 3 + 1] = y
        positions[particleIndex * 3 + 2] = z

        colors[particleIndex * 3] = particleData.color.r
        colors[particleIndex * 3 + 1] = particleData.color.g
        colors[particleIndex * 3 + 2] = particleData.color.b

        sizes[particleIndex] = particleData.size
        energies[particleIndex] = particleData.energy
        alphas[particleIndex] = 1.0

        scene.particlePositions![particleIndex * 3] = x
        scene.particlePositions![particleIndex * 3 + 1] = y
        scene.particlePositions![particleIndex * 3 + 2] = z

        scene.particlesData!.push(particleData)
        particleIndex++
      })

      // Create particles for away team players (20 players, gray particles)
      game.awayRoster.slice(0, 20).forEach((player, playerIndex) => {
        if (particleIndex >= maxParticleCount) return

        const particleData: ParticleData = {
          id: player.id,
          position: new THREE.Vector3(),
          velocity: new THREE.Vector3(
            -0.005 + Math.random() * 0.01,
            -0.005 + Math.random() * 0.01,
            -0.005 + Math.random() * 0.01
          ),
          size: 4, // Larger particles for players
          color: { r: 0.6, g: 0.6, b: 0.6 }, // Gray for away team
          playerId: player.id,
          team: 'away',
          jerseyNumber: player.jerseyNumber,
          name: player.name,
          connections: [],
          clusterPosition: new THREE.Vector3(),
          gameId: game.id,
          numConnections: 0,
          energy: 0.3 + Math.random() * 0.4, // Slightly lower base energy for away team
          trail: [] // Initialize trail array
        }

        // Create physics body for realistic interactions
        const physicsShape = new CANNON.Sphere(2)
        // Position players in a sphere around the game center (offset from home team)
        const angle = (playerIndex / 20) * Math.PI * 2 + Math.PI * 0.6 // Reduced offset (108 degrees)
        const radius = 120 + Math.random() * 60 // Increased radius for better spacing
        const heightOffset = (playerIndex % 4 - 2) * 40 // Increased height spread for better separation

        const x = gameCenter.x + Math.cos(angle) * radius
        const y = gameCenter.y + heightOffset
        const z = gameCenter.z + Math.sin(angle) * radius

        particleData.physicsBody = new CANNON.Body({
          mass: 1,
          position: new CANNON.Vec3(x, y, z),
          velocity: new CANNON.Vec3(
            particleData.velocity.x * 100,
            particleData.velocity.y * 100,
            particleData.velocity.z * 100
          ),
          material: new CANNON.Material({ friction: 0.1, restitution: 0.8 })
        })

        particleData.physicsBody.addShape(physicsShape)
        scene.physicsWorld!.addBody(particleData.physicsBody)

        particleData.position.set(x, y, z)
        particleData.clusterPosition.copy(particleData.position)

        // Set shader attributes for the particle
        if (!scene.particles) return
        const positions = scene.particles.attributes.position.array as Float32Array
        const colors = scene.particles.attributes.color.array as Float32Array
        const sizes = scene.particles.attributes.size.array as Float32Array
        const energies = scene.particles.attributes.energy.array as Float32Array
        const alphas = scene.particles.attributes.alpha.array as Float32Array

        positions[particleIndex * 3] = x
        positions[particleIndex * 3 + 1] = y
        positions[particleIndex * 3 + 2] = z

        colors[particleIndex * 3] = particleData.color.r
        colors[particleIndex * 3 + 1] = particleData.color.g
        colors[particleIndex * 3 + 2] = particleData.color.b

        sizes[particleIndex] = particleData.size
        energies[particleIndex] = particleData.energy
        alphas[particleIndex] = 1.0

        scene.particlePositions![particleIndex * 3] = x
        scene.particlePositions![particleIndex * 3 + 1] = y
        scene.particlePositions![particleIndex * 3 + 2] = z

        scene.particlesData!.push(particleData)
        particleIndex++
      })

      // Build player connections based on game events
      const playerParticles = scene.particlesData!.slice(-40) // Last 40 particles are players

      game.events.forEach(event => {
        if (event.players && event.players.length > 1) {
          // Find player particles involved in this event
          const involvedPlayers = playerParticles.filter(p =>
            event.players!.includes(p.playerId)
          )

          // Create connections between all players involved in the same event
          for (let i = 0; i < involvedPlayers.length; i++) {
            for (let j = i + 1; j < involvedPlayers.length; j++) {
              const playerA = involvedPlayers[i]
              const playerB = involvedPlayers[j]

              // Add connection if not already exists
              if (!playerA.connections.includes(playerB.playerId)) {
                playerA.connections.push(playerB.playerId)
                console.log(`Created connection: ${playerA.playerId} ↔ ${playerB.playerId} (event: ${event.label})`)
              }
              if (!playerB.connections.includes(playerA.playerId)) {
                playerB.connections.push(playerA.playerId)
              }

              // Update interaction counts
              const playerANode = game.homeRoster.find(p => p.id === playerA.playerId) ||
                                 game.awayRoster.find(p => p.id === playerA.playerId)
              const playerBNode = game.homeRoster.find(p => p.id === playerB.playerId) ||
                                 game.awayRoster.find(p => p.id === playerB.playerId)

              if (playerANode) playerANode.interactionCount++
              if (playerBNode) playerBNode.interactionCount++
            }
          }
        }
      })
    })

    // If we have space, fill remaining particles with subtle background particles
    for (let i = particleIndex; i < maxParticleCount && i < particleIndex + 100; i++) {
      const particleData: ParticleData = {
        id: `background-${i}`,
        position: new THREE.Vector3(),
        velocity: new THREE.Vector3(
          -0.0005 + Math.random() * 0.001,
          -0.0005 + Math.random() * 0.001,
          -0.0005 + Math.random() * 0.001
        ),
        size: 1.5,
        color: { r: 0.3, g: 0.3, b: 0.3 },
        playerId: `background-${i}`,
        team: 'home', // Doesn't matter for background
        jerseyNumber: '00',
        name: 'Background',
        connections: [],
        clusterPosition: new THREE.Vector3(),
        gameId: 'background',
        numConnections: 0,
        energy: 0.1 + Math.random() * 0.2, // Low energy for background particles
        trail: [] // Initialize trail array
      }

      // Create lightweight physics body for background particles
      const physicsShape = new CANNON.Sphere(0.5)
      const x = (Math.random() - 0.5) * r * 1.2
      const y = (Math.random() - 0.5) * r * 0.8
      const z = (Math.random() - 0.5) * r * 1.2

      particleData.physicsBody = new CANNON.Body({
        mass: 0.1, // Lighter mass for background particles
        position: new CANNON.Vec3(x, y, z),
        velocity: new CANNON.Vec3(
          particleData.velocity.x * 100,
          particleData.velocity.y * 100,
          particleData.velocity.z * 100
        ),
        material: new CANNON.Material({ friction: 0.05, restitution: 0.9 })
      })
      particleData.physicsBody.addShape(physicsShape)
      scene.physicsWorld!.addBody(particleData.physicsBody)

      particleData.position.set(x, y, z)

      // Set shader attributes for the particle
      const positions = scene.particles.attributes.position.array as Float32Array
      const colors = scene.particles.attributes.color.array as Float32Array
      const sizes = scene.particles.attributes.size.array as Float32Array
      const energies = scene.particles.attributes.energy.array as Float32Array
      const alphas = scene.particles.attributes.alpha.array as Float32Array

      positions[particleIndex * 3] = x
      positions[particleIndex * 3 + 1] = y
      positions[particleIndex * 3 + 2] = z

      colors[particleIndex * 3] = particleData.color.r
      colors[particleIndex * 3 + 1] = particleData.color.g
      colors[particleIndex * 3 + 2] = particleData.color.b

      sizes[particleIndex] = particleData.size
      energies[particleIndex] = particleData.energy
      alphas[particleIndex] = 1.0

      scene.particlePositions![particleIndex * 3] = x
      scene.particlePositions![particleIndex * 3 + 1] = y
      scene.particlePositions![particleIndex * 3 + 2] = z

      scene.particlesData!.push(particleData)
      particleIndex++
    }

    // Mark geometry attributes as needing updates
    scene.particles.attributes.position.needsUpdate = true
    scene.particles.attributes.color.needsUpdate = true
    scene.particles.attributes.size.needsUpdate = true
    scene.particles.attributes.energy.needsUpdate = true
    scene.particles.attributes.alpha.needsUpdate = true

    // Create advanced connection line system with energy flow
    const connectionGeometry = new THREE.BufferGeometry()
    connectionGeometry.setAttribute('position', new THREE.BufferAttribute(scene.positions, 3).setUsage(THREE.DynamicDrawUsage))
    connectionGeometry.setAttribute('color', new THREE.BufferAttribute(scene.colors, 3).setUsage(THREE.DynamicDrawUsage))
    connectionGeometry.setAttribute('alpha', new THREE.BufferAttribute(new Float32Array(maxParticleCount * maxParticleCount), 1).setUsage(THREE.DynamicDrawUsage))
    connectionGeometry.computeBoundingSphere()
    connectionGeometry.setDrawRange(0, 0)

    // Use the same connection material for main connections
    scene.linesMesh = new THREE.LineSegments(connectionGeometry, scene.connectionMaterial)
    scene.scene.add(scene.linesMesh)


    // Enhanced animation loop with physics and advanced effects
    const animate = () => {
      scene.time += 0.016 // ~60fps delta time

      // Update TWEEN animations
      TWEEN.update()

      // Step physics world
      scene.physicsWorld!.fixedStep(1/60)

      let vertexpos = 0
      let colorpos = 0
      let numConnected = 0
      let trailVertexPos = 0
      let trailColorPos = 0

      // Reset connections
      for (let i = 0; i < particleCount; i++) {
        scene.particlesData![i].numConnections = 0
      }

      // Update particles with physics and advanced effects
      for (let i = 0; i < particleCount; i++) {
        const particleData = scene.particlesData![i]

        // Sync Three.js positions with CANNON.js physics bodies
        if (particleData.physicsBody) {
          const physicsPos = particleData.physicsBody.position
          const physicsVel = particleData.physicsBody.velocity

          // Apply cluster attraction as physics force
          if (particleData.clusterPosition) {
            const currentPos = new THREE.Vector3(physicsPos.x, physicsPos.y, physicsPos.z)
            const toCluster = particleData.clusterPosition.clone().sub(currentPos)
            const distance = toCluster.length()

            if (distance > 10) { // Apply force if far from cluster
              const attractionStrength = Math.min(distance / 100, 5) // Physics scale
              const force = toCluster.normalize().multiplyScalar(attractionStrength)
              particleData.physicsBody.applyForce(new CANNON.Vec3(force.x, force.y, force.z))
            }
          }

          // Apply gentle damping to physics velocity
          particleData.physicsBody.velocity.scale(0.995)

          // Update Three.js positions from physics
          scene.particlePositions![i * 3] = physicsPos.x
          scene.particlePositions![i * 3 + 1] = physicsPos.y
          scene.particlePositions![i * 3 + 2] = physicsPos.z

          // Update energy based on velocity and connections
          const speed = Math.sqrt(physicsVel.x * physicsVel.x + physicsVel.y * physicsVel.y + physicsVel.z * physicsVel.z)
          particleData.energy = Math.max(0.1, Math.min(1.0, particleData.energy * 0.98 + (speed / 50 + particleData.numConnections / 10) * 0.02))
        }

        // Update particle trail for motion blur effect
        if (particleData.trail) {
          const currentPos = new THREE.Vector3(
            scene.particlePositions![i * 3],
            scene.particlePositions![i * 3 + 1],
            scene.particlePositions![i * 3 + 2]
          )

          particleData.trail.unshift(currentPos.clone())
          if (particleData.trail.length > 20) {
            particleData.trail.pop()
          }

          // Add trail segments to geometry
          for (let t = 0; t < Math.min(particleData.trail.length - 1, 19); t++) {
            if (trailVertexPos < scene.trailsGeometry!.attributes.position.array.length - 6) {
              const pos1 = particleData.trail[t]
              const pos2 = particleData.trail[t + 1]
              const alpha = 1.0 - (t / 20)

              // Line segment positions
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos1.x
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos1.y
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos1.z
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos2.x
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos2.y
              scene.trailsGeometry!.attributes.position.array[trailVertexPos++] = pos2.z

              // Line colors (inherit particle color with fading alpha)
              for (let c = 0; c < 6; c++) {
                scene.trailsGeometry!.attributes.color.array[trailColorPos++] = particleData.color.r * alpha
                scene.trailsGeometry!.attributes.color.array[trailColorPos++] = particleData.color.g * alpha
                scene.trailsGeometry!.attributes.color.array[trailColorPos++] = particleData.color.b * alpha
              }
            }
          }
        }

        // Very subtle boundary collision
        const boundaryForce = 0.001
        if (scene.particlePositions![i * 3 + 1] < -rHalf) {
          particleData.velocity.y += boundaryForce
        } else if (scene.particlePositions![i * 3 + 1] > rHalf) {
          particleData.velocity.y -= boundaryForce
        }
        if (scene.particlePositions![i * 3] < -rHalf) {
          particleData.velocity.x += boundaryForce
        } else if (scene.particlePositions![i * 3] > rHalf) {
          particleData.velocity.x -= boundaryForce
        }
        if (scene.particlePositions![i * 3 + 2] < -rHalf) {
          particleData.velocity.z += boundaryForce
        } else if (scene.particlePositions![i * 3 + 2] > rHalf) {
          particleData.velocity.z -= boundaryForce
        }

        // Add repulsion forces between nearby particles (prevents overcrowding)
        for (let j = 0; j < particleCount; j++) {
          if (i === j) continue

          const particleDataB = scene.particlesData![j]
          const dx = scene.particlePositions![i * 3] - scene.particlePositions![j * 3]
          const dy = scene.particlePositions![i * 3 + 1] - scene.particlePositions![j * 3 + 1]
          const dz = scene.particlePositions![i * 3 + 2] - scene.particlePositions![j * 3 + 2]
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)

          // Increased repulsion for neural network scattering
          const minSeparation = 25
          if (dist < minSeparation && dist > 0) {
            const repulsionStrength = 0.001 * (1 - dist / minSeparation)
            const repulsionVector = new THREE.Vector3(dx, dy, dz).normalize().multiplyScalar(repulsionStrength)
            particleData.velocity.add(repulsionVector)
          }
        }

        // Check connections to other player particles
        for (let j = i + 1; j < particleCount; j++) {
          const particleDataB = scene.particlesData![j]

          // Skip non-player particles (background particles)
          if (particleData.gameId === 'background' || particleDataB.gameId === 'background') continue

          const dx = scene.particlePositions![i * 3] - scene.particlePositions![j * 3]
          const dy = scene.particlePositions![i * 3 + 1] - scene.particlePositions![j * 3 + 1]
          const dz = scene.particlePositions![i * 3 + 2] - scene.particlePositions![j * 3 + 2]
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz)

          // Check if these players are connected (have interacted)
          const areConnectedPlayers = particleData.connections.includes(particleDataB.playerId) ||
                                     particleDataB.connections.includes(particleData.playerId)

          // Debug: Log connection status occasionally
          if (Math.random() < 0.001 && areConnectedPlayers) {
            console.log(`Connection found: ${particleData.playerId} ↔ ${particleDataB.playerId}`)
          }

          if (areConnectedPlayers) {
            const connectionDistance = 500.0 // Increased distance for neural network connections

          if (dist < connectionDistance) {
            particleData.numConnections++
            particleDataB.numConnections++

              // Calculate alpha based on distance (more visible connections)
              const distanceAlpha = 1.0 - dist / connectionDistance
              const alpha = Math.min(1.0, Math.max(0.3, distanceAlpha * 0.8)) // Stronger minimum alpha

              // Skip very weak connections
              if (alpha > 0.1) {
                // Very subtle connection forces for neural network behavior
                const connectionForce = 0.0001 * alpha
                const connectionVector = new THREE.Vector3(dx, dy, dz).normalize().multiplyScalar(connectionForce)

                // Apply gentle attraction along connections
                particleData.velocity.add(connectionVector.clone().multiplyScalar(0.5))
                particleDataB.velocity.add(connectionVector.clone().multiplyScalar(-0.5))

            // Line vertices
            scene.positions![vertexpos++] = scene.particlePositions![i * 3]
            scene.positions![vertexpos++] = scene.particlePositions![i * 3 + 1]
            scene.positions![vertexpos++] = scene.particlePositions![i * 3 + 2]

            scene.positions![vertexpos++] = scene.particlePositions![j * 3]
            scene.positions![vertexpos++] = scene.particlePositions![j * 3 + 1]
            scene.positions![vertexpos++] = scene.particlePositions![j * 3 + 2]

                // Line colors based on team relationship
                let r = 0.7, g = 0.7, b = 0.7 // default gray

                if (particleData.team === particleDataB.team) {
                  // Same team connections - white/bright
                  r = 1.0; g = 1.0; b = 1.0
                } else {
                  // Cross-team connections - red/gray mixed
                  r = 0.8; g = 0.3; b = 0.3
                }

                // Apply alpha to colors
                scene.colors![colorpos++] = r * alpha
                scene.colors![colorpos++] = g * alpha
                scene.colors![colorpos++] = b * alpha

                scene.colors![colorpos++] = r * alpha
                scene.colors![colorpos++] = g * alpha
                scene.colors![colorpos++] = b * alpha

                // Set alpha attribute for shader (one per vertex)
                const alphaArray = connectionGeometry.attributes.alpha.array as Float32Array
                const alphaIndex = (vertexpos / 3) - 2  // Convert from position index to alpha index
                alphaArray[alphaIndex] = alpha      // First vertex alpha
                alphaArray[alphaIndex + 1] = alpha  // Second vertex alpha

            numConnected++
              }
            }
          }
        }
      }

      // Update geometries and shaders
      scene.linesMesh!.geometry.setDrawRange(0, numConnected * 2)
      scene.linesMesh!.geometry.attributes.position.needsUpdate = true
      scene.linesMesh!.geometry.attributes.color.needsUpdate = true
      scene.linesMesh!.geometry.attributes.alpha.needsUpdate = true
      connectionGeometry.attributes.alpha.needsUpdate = true

      // Debug: Log connection count occasionally
      if (Math.random() < 0.01) {
        console.log(`Drawing ${numConnected} connections (${numConnected * 2} vertices)`)
      }

      scene.pointCloud!.geometry.attributes.position.needsUpdate = true
      scene.pointCloud!.geometry.attributes.color.needsUpdate = true
      scene.pointCloud!.geometry.attributes.size.needsUpdate = true
      scene.pointCloud!.geometry.attributes.energy.needsUpdate = true
      scene.pointCloud!.geometry.attributes.alpha.needsUpdate = true

      // Update trail geometry
      scene.trailsMesh!.geometry.setDrawRange(0, trailVertexPos / 3)
      scene.trailsGeometry!.attributes.position.needsUpdate = true
      scene.trailsGeometry!.attributes.color.needsUpdate = true

      // Update shader uniforms
      if (scene.particleMaterial) {
        scene.particleMaterial.uniforms.time.value = scene.time
      }
      if (scene.connectionMaterial) {
        scene.connectionMaterial.uniforms.time.value = scene.time
      }

      // Update controls
      if (scene.controls) {
        scene.controls.update()
      }

      // Animate dynamic lighting for futuristic atmosphere
      const time = scene.time
      if (scene.scene) {
        const ambientLight = scene.scene.getObjectByName('ambientLight') as THREE.AmbientLight
        if (ambientLight) {
          ambientLight.intensity = 0.3 + Math.sin(time * 0.5) * 0.1
        }
      }

      // Update badge positions
      const tempBadges: typeof badges = []


      // Add player badges with jersey numbers (show all players)
      for (let i = 0; i < particleCount && tempBadges.length < 120; i++) {
        const particleData = scene.particlesData![i]
        if (particleData.gameId !== 'background') {
          // Find interaction count from roster
          const game = allGames.find(g => g.id === particleData.gameId)
          if (game) {
            const playerNode = game.homeRoster.find(p => p.id === particleData.playerId) ||
                              game.awayRoster.find(p => p.id === particleData.playerId)
            if (playerNode) {
              const interactions = playerNode.interactionCount

          const vector = new THREE.Vector3(
            scene.particlePositions![i * 3],
            scene.particlePositions![i * 3 + 1],
            scene.particlePositions![i * 3 + 2]
          )
          
          // Project 3D position to 2D screen coordinates
          vector.project(scene.camera!)
          
              if (vector.z < 1) { // Only show if in front of camera
          const x = (vector.x * 0.5 + 0.5) * container.clientWidth
          const y = (-(vector.y * 0.5) + 0.5) * container.clientHeight
          
          tempBadges.push({
                  id: `player-${particleData.playerId}`,
                  x,
                  y,
                  type: 'player',
                  label: particleData.jerseyNumber, // Just show jersey number, no interaction count
                  visible: true,
                  gameId: particleData.gameId,
                  team: particleData.team // Add team information for styling
                })
              }
            }
          }
        }
      }
      setBadges(tempBadges)

      // Render with post-processing effects for futuristic look
      if (scene.composer) {
        scene.composer.render()
      } else {
        scene.renderer!.render(scene.scene!, scene.camera!)
      }
      scene.animationId = requestAnimationFrame(animate)
    }

    animate()

    // Handle resize with composer update
    const handleResize = () => {
      if (!container || !scene.camera || !scene.renderer) return

      scene.camera.aspect = container.clientWidth / container.clientHeight
      scene.camera.updateProjectionMatrix()
      scene.renderer.setSize(container.clientWidth, container.clientHeight)
      if (scene.composer) {
        scene.composer.setSize(container.clientWidth, container.clientHeight)
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      
      if (scene.animationId) {
        cancelAnimationFrame(scene.animationId)
      }
      
      if (scene.controls) {
        scene.controls.dispose()
      }
      
      if (scene.renderer && container.contains(scene.renderer.domElement)) {
        container.removeChild(scene.renderer.domElement)
      }
      
      // Dispose advanced Three.js resources
      scene.particles?.dispose()
      scene.linesMesh?.geometry.dispose()
      scene.trailsGeometry?.dispose()

      if (scene.pointCloud?.material) {
        if (Array.isArray(scene.pointCloud.material)) {
          scene.pointCloud.material.forEach(m => m.dispose())
        } else {
          scene.pointCloud.material.dispose()
        }
      }
      if (scene.linesMesh?.material) {
        if (Array.isArray(scene.linesMesh.material)) {
          scene.linesMesh.material.forEach(m => m.dispose())
        } else {
          scene.linesMesh.material.dispose()
        }
      }
      if (scene.trailsMesh?.material) {
        if (Array.isArray(scene.trailsMesh.material)) {
          scene.trailsMesh.material.forEach(m => m.dispose())
        } else {
          scene.trailsMesh.material.dispose()
        }
      }

      scene.composer?.dispose()
      scene.renderer?.dispose()

      // Dispose physics world
      scene.physicsWorld?.bodies.forEach(body => {
        scene.physicsWorld!.removeBody(body)
      })
      
      // Clear references
      sceneRef.current = { time: 0 }
    }
  }, [])

  const allGamesForUI = games || defaultGames

  // Mouse hover detection for player particles
  const handleMouseMove = (event: React.MouseEvent<HTMLDivElement>) => {
    if (!containerRef.current || !sceneRef.current?.camera) return

    const scene = sceneRef.current
    const camera = scene.camera
    if (!camera) return

    const rect = containerRef.current.getBoundingClientRect()
    const mouseX = ((event.clientX - rect.left) / rect.width) * 2 - 1
    const mouseY = -((event.clientY - rect.top) / rect.height) * 2 + 1

    // Create a ray from camera through mouse position
    const raycaster = new THREE.Raycaster()
    raycaster.setFromCamera(new THREE.Vector2(mouseX, mouseY), camera)

    let closestParticle: {
      id: string
      name: string
      jerseyNumber: string
      team: 'home' | 'away'
      x: number
      y: number
    } | null = null
    let closestDistance = Infinity

    // Check distance from ray to each particle
    if (scene.particlesData && scene.particlePositions) {
      const particleCount = scene.particlesData.length
      for (let i = 0; i < particleCount; i++) {
        const particleData = scene.particlesData[i]
        if (particleData.gameId === 'background') continue // Skip background particles

        const particlePos = new THREE.Vector3(
          scene.particlePositions[i * 3],
          scene.particlePositions[i * 3 + 1],
          scene.particlePositions[i * 3 + 2]
        )

        // Calculate distance from ray to particle
        const distance = raycaster.ray.distanceToPoint(particlePos)

        // Also check if particle is in front of camera
        const cameraToParticle = particlePos.clone().sub(camera.position)
        const cameraDirection = camera.getWorldDirection(new THREE.Vector3())
        const dotProduct = cameraToParticle.dot(cameraDirection)

        if (distance < 50 && dotProduct > 0 && distance < closestDistance) { // 50 unit hover radius
          // Project particle to screen coordinates for tooltip positioning
          const screenPos = particlePos.clone()
          screenPos.project(camera)

          if (screenPos.z < 1) {
            const x = (screenPos.x * 0.5 + 0.5) * rect.width + rect.left
            const y = (-(screenPos.y * 0.5) + 0.5) * rect.height + rect.top

            closestParticle = {
              id: particleData.id,
              name: particleData.name,
              jerseyNumber: particleData.jerseyNumber,
              team: particleData.team,
              x,
              y
            }
            closestDistance = distance
          }
        }
      }
    }

    setHoveredParticle(closestParticle)
  }

  return (
    <div className="relative w-full h-full">


      {/* Player Hover Tooltip */}
      {hoveredParticle && (
        <div
          className="absolute z-50 pointer-events-none bg-black/90 backdrop-blur-sm border border-gray-600 rounded-lg px-3 py-2 shadow-lg"
          style={{
            left: `${hoveredParticle.x + 10}px`,
            top: `${hoveredParticle.y - 10}px`,
            transform: 'translate(-50%, -100%)'
          }}
        >
          <div className="text-white text-sm font-military-display font-bold">
            {hoveredParticle.name}
          </div>
          <div className={`text-xs font-military-display ${
            hoveredParticle.team === 'home' ? 'text-red-400' : 'text-gray-400'
          }`}>
            #{hoveredParticle.jerseyNumber} • {hoveredParticle.team.toUpperCase()} TEAM
          </div>
        </div>
      )}

      {/* Military Neural Network Legend */}
      <div className="absolute top-4 right-4 z-50 bg-black/95 backdrop-blur-sm border border-gray-600 rounded-lg p-4 shadow-xl">
        <div className="text-gray-300 text-xs font-mono space-y-1">
          <div className="text-white font-bold mb-2 border-b border-gray-600 pb-1">NEURAL NETWORK STATUS</div>
          <div><span className="text-red-400 font-bold">RED NODES</span>: Home Team Players</div>
          <div><span className="text-gray-400 font-bold">GRAY NODES</span>: Away Team Players</div>
          <div><span className="text-gray-200 font-bold">MOTION TRAILS</span>: Velocity Visualization</div>
          <div><span className="text-white font-bold">WHITE LINKS</span>: Team Connections</div>
          <div><span className="text-red-400 font-bold">RED LINKS</span>: Cross-Team Interactions</div>
          <div><span className="text-gray-300 font-bold">ENERGY GLOW</span>: Active Network Nodes</div>
          <div className="text-gray-400 mt-2 border-t border-gray-600 pt-1 text-[10px]">PHYSICS SIMULATION • REAL-TIME</div>
        </div>
      </div>

      <div 
        ref={containerRef}
        className={`relative w-full h-full cursor-grab active:cursor-grabbing ${className}`}
        style={{ minHeight: '500px' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredParticle(null)}
      />
      
      {/* Modern Floating Number Badges */}
      <div className="absolute inset-0 pointer-events-none" ref={labelsContainerRef}>
        {badges.map((badge) => badge.visible && badge.type === 'player' && (
          <div
            key={badge.id}
            className="absolute transform -translate-x-1/2 -translate-y-2 pointer-events-none select-none"
            style={{
              left: `${badge.x}px`,
              top: `${badge.y}px`,
              zIndex: 100
            }}
          >
            <div className={`
              text-sm font-mono font-bold tracking-wider
              drop-shadow-[0_0_8px_rgba(255,0,0,0.8)]
              filter brightness-110 contrast-125
              text-shadow:
                0 0 5px currentColor,
                0 0 10px currentColor,
                0 0 15px currentColor,
                0 0 20px currentColor
              ${badge.team === 'home'
                ? 'text-red-400'
                : 'text-gray-400'
              }
            `}>
              {badge.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
