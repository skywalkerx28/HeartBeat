'use client'

import React, { useRef, useEffect, useState } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'

interface HockeyRink3DProps {
  className?: string
}

export const HockeyRink3D: React.FC<HockeyRink3DProps> = ({ className = '' }) => {
  const mountRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const controlsRef = useRef<OrbitControls | null>(null)
  const animationFrameRef = useRef<number | null>(null)
  const [testStatus, setTestStatus] = useState<string>('Running tests...')

  // Rink constants (feet)
  const RINK_L = 200, RINK_W = 85, CORNER_R = 28
  const HALF_L = RINK_L / 2, HALF_W = RINK_W / 2

  const GOAL_LINE_FROM_END = 11
  const GOAL_LINE_X = HALF_L - GOAL_LINE_FROM_END // 89

  const BLUE_FROM_CENTER = 25
  const LINE_THICK = 1, GOAL_LINE_THICK = 0.4

  const FACE_CIRCLE_R = 15, DOT_R = 1.0, LATERAL_FROM_BOARD = 22
  const FACE_Z = HALF_W - LATERAL_FROM_BOARD // 20.5
  const END_CIRCLE_X = GOAL_LINE_X - 20 // 69
  const NEUTRAL_DOT_X = BLUE_FROM_CENTER - 5 // 20

  const BOARDS_THICK = 1.0, BOARDS_H = 8.0

  const GLASS_THICK = 0.6, GLASS_H = 10.0
  const SHOW_GLASS = false // windows removed

  const GOAL_WIDTH = 6, GOAL_HEIGHT = 4, GOAL_DEPTH = 3
  const Z_EPS = 0.02

  // Helpers
  const roundedRectShape = (hw: number, hh: number, radius: number): THREE.Shape => {
    const s = new THREE.Shape()
    s.moveTo(hw - radius, hh)
    s.absarc(hw - radius, hh - radius, radius, 0, Math.PI/2, false)
    s.lineTo(-hw + radius, hh)
    s.absarc(-hw + radius, hh - radius, radius, Math.PI/2, Math.PI, false)
    s.lineTo(-hw, -hh + radius)
    s.absarc(-hw + radius, -hh + radius, radius, Math.PI, Math.PI * 1.5, false)
    s.lineTo(hw - radius, -hh)
    s.absarc(hw - radius, -hh + radius, radius, Math.PI * 1.5, Math.PI * 2.0, false)
    s.lineTo(hw, hh - radius)
    return s
  }

  // Initialize Three.js scene
  useEffect(() => {
    if (!mountRef.current) return

    const root = mountRef.current

    // Scene / Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setSize(root.clientWidth, root.clientHeight)
    renderer.shadowMap.enabled = true
    root.appendChild(renderer.domElement)
    rendererRef.current = renderer

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x0b0e1a)
    sceneRef.current = scene

    // Camera + controls
    const camera = new THREE.PerspectiveCamera(45, root.clientWidth / root.clientHeight, 0.1, 2000)
    camera.position.set(180, 120, 220)
    camera.lookAt(0, 0, 0)
    cameraRef.current = camera

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.06
    controls.minDistance = 60
    controls.maxDistance = 600
    controls.maxPolarAngle = Math.PI * 0.49
    controls.target.set(0, 0, 0)
    controlsRef.current = controls

    // Lights
    scene.add(new THREE.HemisphereLight(0xffffff, 0x223355, 0.65))
    const dir = new THREE.DirectionalLight(0xffffff, 0.7)
    dir.position.set(200, 300, 150)
    dir.castShadow = true
    dir.shadow.mapSize.set(2048, 2048)
    scene.add(dir)

    // Floor shadow
    const shadowPlane = new THREE.Mesh(
      new THREE.PlaneGeometry(500, 500),
      new THREE.ShadowMaterial({ opacity: 0.25 })
    )
    shadowPlane.rotation.x = -Math.PI/2
    shadowPlane.position.y = -0.1
    shadowPlane.receiveShadow = true
    scene.add(shadowPlane)

    // Ice
    const iceShape = roundedRectShape(HALF_L, HALF_W, CORNER_R)
    const iceGeom = new THREE.ShapeGeometry(iceShape, 64)
    const iceMat = new THREE.MeshPhysicalMaterial({
      color: 0xeff3ff,
      roughness: 0.8,
      metalness: 0.0,
      reflectivity: 0.2,
      clearcoat: 0.05
    })
    const ice = new THREE.Mesh(iceGeom, iceMat)
    ice.name = 'ice'
    ice.rotation.x = -Math.PI/2
    ice.receiveShadow = true
    scene.add(ice)

    // Boards
    const outerBoards = roundedRectShape(HALF_L + BOARDS_THICK, HALF_W + BOARDS_THICK, CORNER_R + BOARDS_THICK)
    outerBoards.holes.push(iceShape)
    const boardsExtrude = new THREE.ExtrudeGeometry(outerBoards, { depth: BOARDS_H, bevelEnabled: false, curveSegments: 64 })
    const boardsMat = new THREE.MeshStandardMaterial({ color: 0xf5f7ff })
    const boards = new THREE.Mesh(boardsExtrude, boardsMat)
    boards.name = 'boards'
    boards.rotation.x = -Math.PI/2
    boards.castShadow = true
    boards.receiveShadow = true
    scene.add(boards)

    // Bell Centre-style tribunes (two bowls)
    const SHOW_TRIBUNES = true
    const TRIBUNE_TREAD = 6, TRIBUNE_RISE = 2, GAP_CONCOURSE = 10
    const ROWS_LOWER = 12, ROWS_UPPER = 16

    const addBowl = (rows: number, startOffset: number, startHeight: number, name: string): THREE.Group => {
      const group = new THREE.Group()
      group.name = name
      const seatTop = new THREE.MeshStandardMaterial({ color: 0x9b0d16, metalness: 0.0, roughness: 0.8 })
      const riser = new THREE.MeshStandardMaterial({ color: 0x6e0a10, metalness: 0.0, roughness: 0.9 })

      for (let i = 0; i < rows; i++){
        const innerL = HALF_L + BOARDS_THICK + startOffset + i*TRIBUNE_TREAD
        const innerW = HALF_W + BOARDS_THICK + startOffset + i*TRIBUNE_TREAD
        const innerR = CORNER_R + BOARDS_THICK + startOffset + i*TRIBUNE_TREAD
        const outerL = innerL + TRIBUNE_TREAD
        const outerW = innerW + TRIBUNE_TREAD
        const outerR = innerR + TRIBUNE_TREAD

        const topShape = roundedRectShape(outerL, outerW, outerR)
        topShape.holes.push(roundedRectShape(innerL, innerW, innerR))
        const topGeom = new THREE.ShapeGeometry(topShape, 48)
        const top = new THREE.Mesh(topGeom, seatTop)
        top.rotation.x = -Math.PI/2
        top.position.y = startHeight + i*TRIBUNE_RISE
        top.receiveShadow = true
        group.add(top)

        const riserGeom = new THREE.ExtrudeGeometry(roundedRectShape(outerL, outerW, outerR), { depth: TRIBUNE_RISE, bevelEnabled: false, curveSegments: 48 })
        const riserMesh = new THREE.Mesh(riserGeom, riser)
        riserMesh.rotation.x = -Math.PI/2
        riserMesh.position.y = startHeight + i*TRIBUNE_RISE - TRIBUNE_RISE
        riserMesh.receiveShadow = true
        riserMesh.castShadow = true
        group.add(riserMesh)
      }
      scene.add(group)
      return group
    }

    if (SHOW_TRIBUNES){
      const tribunes = new THREE.Group()
      tribunes.name = 'tribunes'
      const lower = addBowl(ROWS_LOWER, 2.5, BOARDS_H + 0.0, 'bowl-lower')
      tribunes.add(lower)
      const startOffsetUpper = 2.5 + ROWS_LOWER*TRIBUNE_TREAD + GAP_CONCOURSE
      const startHeightUpper = BOARDS_H + ROWS_LOWER*TRIBUNE_RISE + 6
      const upper = addBowl(ROWS_UPPER, startOffsetUpper, startHeightUpper, 'bowl-upper')
      tribunes.add(upper)
      scene.add(tribunes)
    }

    // Lines & circles
    const stripes: THREE.Mesh[] = [], circles: THREE.Mesh[] = []

    const addStripe = (x1: number, x2: number, z1: number, z2: number, color: number, tag?: string): THREE.Mesh => {
      const w = Math.abs(x2 - x1) || LINE_THICK, h = Math.abs(z2 - z1) || LINE_THICK
      const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide }))
      m.rotation.x = -Math.PI/2
      m.position.set((x1+x2)/2, Z_EPS, (z1+z2)/2)
      m.userData.tag = tag || ''
      scene.add(m)
      stripes.push(m)
      return m
    }

    const addCircle = (x: number, z: number, radius: number, color: number, ring: boolean = false, thickness: number = 1, tag?: string): THREE.Mesh => {
      const geom = ring ? new THREE.RingGeometry(Math.max(radius - thickness, 0.01), radius, 64)
                        : new THREE.CircleGeometry(radius, 64)
      const m = new THREE.Mesh(geom, new THREE.MeshBasicMaterial({ color, side: THREE.DoubleSide }))
      m.rotation.x = -Math.PI/2
      m.position.set(x, Z_EPS, z)
      m.userData.tag = tag || ''
      scene.add(m)
      circles.push(m)
      return m
    }

    addStripe(-LINE_THICK/2, LINE_THICK/2, -HALF_W, HALF_W, 0xcc2222, 'center')
    addStripe(BLUE_FROM_CENTER - LINE_THICK/2, BLUE_FROM_CENTER + LINE_THICK/2, -HALF_W, HALF_W, 0x2d5eff, 'blue+')
    addStripe(-BLUE_FROM_CENTER - LINE_THICK/2, -BLUE_FROM_CENTER + LINE_THICK/2, -HALF_W, HALF_W, 0x2d5eff, 'blue-')
    addStripe(GOAL_LINE_X - GOAL_LINE_THICK/2, GOAL_LINE_X + GOAL_LINE_THICK/2, -HALF_W, HALF_W, 0xcc2222, 'goal+')
    addStripe(-GOAL_LINE_X - GOAL_LINE_THICK/2, -GOAL_LINE_X + GOAL_LINE_THICK/2, -HALF_W, HALF_W, 0xcc2222, 'goal-')

    addCircle(0, 0, FACE_CIRCLE_R, 0xcc2222, true, 0.7, 'center-circle')
    addCircle(0, 0, DOT_R, 0x0a1340, false, 1, 'center-dot')

    const endCirclePositions: [number, number][] = [
      [END_CIRCLE_X, FACE_Z],
      [END_CIRCLE_X, -FACE_Z],
      [-END_CIRCLE_X, FACE_Z],
      [-END_CIRCLE_X, -FACE_Z]
    ]

    endCirclePositions.forEach(([x, z]: [number, number], i: number) => {
      addCircle(x, z, FACE_CIRCLE_R, 0xcc2222, true, 0.7, `end-circle-${i}`)
      addCircle(x, z, DOT_R, 0x0a1340, false, 1, `end-dot-${i}`)
    })

    const neutralDotPositions: [number, number][] = [
      [NEUTRAL_DOT_X, FACE_Z],
      [NEUTRAL_DOT_X, -FACE_Z],
      [-NEUTRAL_DOT_X, FACE_Z],
      [-NEUTRAL_DOT_X, -FACE_Z]
    ]

    neutralDotPositions.forEach(([x, z]: [number, number], i: number) => {
      addCircle(x, z, DOT_R, 0x0a1340, false, 1, `neutral-dot-${i}`)
    })

    // Goal creases
    const addCrease = (sign: number) => {
      const cx = sign * GOAL_LINE_X, r = 6, rectDepth = 4
      const s = new THREE.Shape()
      const arcStart = sign > 0 ? Math.PI/2 : -Math.PI/2
      const arcEnd = sign > 0 ? Math.PI*1.5 : Math.PI*0.5
      s.moveTo(cx, -r)
      s.lineTo(cx, r)
      s.lineTo(cx - sign*rectDepth, r)
      s.absarc(cx - sign*rectDepth, 0, r, arcStart, arcEnd, sign > 0)
      s.lineTo(cx, -r)
      const m = new THREE.Mesh(
        new THREE.ShapeGeometry(s, 64),
        new THREE.MeshBasicMaterial({ color: 0x2d5eff, opacity: 0.25, transparent: true, side: THREE.DoubleSide })
      )
      m.rotation.x = -Math.PI/2
      m.position.y = Z_EPS
      scene.add(m)
    }
    addCrease(+1)
    addCrease(-1)

    // Goals
    const addGoal = (sign: number) => {
      const postRadius = 0.4
      const postGeom = new THREE.CylinderGeometry(postRadius, postRadius, GOAL_HEIGHT, 16)
      const postMat = new THREE.MeshStandardMaterial({ color: 0xcc2222, metalness: 0.1, roughness: 0.5 })

      const x = sign * GOAL_LINE_X + sign * (postRadius/2)
      const zL = -GOAL_WIDTH/2, zR = GOAL_WIDTH/2

      const leftPost = new THREE.Mesh(postGeom, postMat)
      leftPost.position.set(x, GOAL_HEIGHT/2, zL)
      leftPost.castShadow = true
      leftPost.receiveShadow = true
      scene.add(leftPost)

      const rightPost = new THREE.Mesh(postGeom, postMat)
      rightPost.position.set(x, GOAL_HEIGHT/2, zR)
      rightPost.castShadow = true
      rightPost.receiveShadow = true
      scene.add(rightPost)

      const barGeom = new THREE.CylinderGeometry(postRadius, postRadius, GOAL_WIDTH, 16)
      const crossbar = new THREE.Mesh(barGeom, postMat)
      crossbar.rotation.z = Math.PI/2
      crossbar.position.set(x, GOAL_HEIGHT, 0)
      crossbar.castShadow = true
      crossbar.receiveShadow = true
      scene.add(crossbar)

      const netGeom = new THREE.BoxGeometry(GOAL_DEPTH, GOAL_HEIGHT, GOAL_WIDTH)
      const netMat = new THREE.MeshPhysicalMaterial({ color: 0xffffff, transparent: true, opacity: 0.15, metalness: 0, roughness: 0.2 })
      const net = new THREE.Mesh(netGeom, netMat)
      net.position.set(x - sign*(GOAL_DEPTH/2), GOAL_HEIGHT/2, 0)
      scene.add(net)
      const netEdges = new THREE.LineSegments(new THREE.EdgesGeometry(netGeom), new THREE.LineBasicMaterial({ color: 0xffffff }))
      net.add(netEdges)
    }
    addGoal(+1)
    addGoal(-1)

    // Click-to-pivot on ice
    const raycaster = new THREE.Raycaster(), mouse = new THREE.Vector2()
    const pickOnCanvas = (e: MouseEvent) => {
      const r = renderer.domElement.getBoundingClientRect()
      mouse.set(((e.clientX - r.left)/r.width)*2 - 1, -((e.clientY - r.top)/r.height)*2 + 1)
      raycaster.setFromCamera(mouse, camera)
      const hits = raycaster.intersectObjects([ice], false)
      if (hits.length){
        const p = hits[0].point
        controls.target.copy(p)
        const offset = new THREE.Vector3().subVectors(camera.position, controls.target)
        camera.position.copy(p.clone().add(offset))
      }
    }
    renderer.domElement.addEventListener('pointerdown', e => { if (e.button === 0) pickOnCanvas(e) })

    // Render loop
    const animate = () => {
      animationFrameRef.current = requestAnimationFrame(animate)
      if (controlsRef.current) {
        controlsRef.current.update()
      }
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current)
      }
    }
    animate()

    // Tiny tests
    const TOL = 0.6
    const failures: string[] = []

    const expectClose = (label: string, actual: number, expected: number, tol: number = TOL) => {
      if (Math.abs(actual - expected) > tol) failures.push(`${label}: got ${actual}, want ${expected}±${tol}`)
    }

    const expect = (label: string, cond: boolean) => {
      if (!cond) failures.push(label)
    }

    expect('THREE imported', !!THREE)
    expect('OrbitControls imported', typeof OrbitControls === 'function')
    expect('Renderer attached', !!renderer.domElement && renderer.domElement.parentElement === root)
    expect('Camera positioned', camera.position.length() > 0)
    expect('Ice present', !!scene.getObjectByName('ice'))
    expect('Boards present', !!scene.getObjectByName('boards'))
    expect('Glass removed as requested', !scene.getObjectByName('glass'))

    const center = stripes.find(s => s.userData.tag === 'center')
    const blueP = stripes.find(s => s.userData.tag === 'blue+')
    const blueN = stripes.find(s => s.userData.tag === 'blue-')
    const goalP = stripes.find(s => s.userData.tag === 'goal+')
    const goalN = stripes.find(s => s.userData.tag === 'goal-')

    expect('Center line exists', !!center)
    expect('Blue+ exists', !!blueP)
    expect('Blue- exists', !!blueN)
    expect('Goal+ exists', !!goalP)
    expect('Goal- exists', !!goalN)

    if (center) expectClose('Center line @ x≈0', center.position.x, 0)
    if (blueP)  expectClose('Blue+ @ x≈+25', blueP.position.x, BLUE_FROM_CENTER)
    if (blueN)  expectClose('Blue- @ x≈−25', blueN.position.x, -BLUE_FROM_CENTER)
    if (goalP)  expectClose('Goal+ @ x≈+89', goalP.position.x, GOAL_LINE_X)
    if (goalN)  expectClose('Goal- @ x≈−89', goalN.position.x, -GOAL_LINE_X)

    if (failures.length) {
      console.warn('[Rink Test Failures]', failures)
      setTestStatus(`Tests: ${failures.length} failed — open console for details.`)
    } else {
      setTestStatus('Tests: all passed ✅')
    }

    // Resize handler
    const handleResize = () => {
      if (renderer && camera && root) {
        renderer.setSize(root.clientWidth, root.clientHeight)
        camera.aspect = root.clientWidth / root.clientHeight
        camera.updateProjectionMatrix()
      }
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
      if (renderer && renderer.domElement && renderer.domElement.parentElement) {
        renderer.domElement.parentElement.removeChild(renderer.domElement)
      }
      renderer.dispose()
      // Clean up geometries and materials
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose()
          if (Array.isArray(object.material)) {
            object.material.forEach(material => material.dispose())
          } else {
            object.material.dispose()
          }
        }
      })
    }
  }, [])

  return (
    <div className={`relative w-full h-full ${className}`}>
      <div ref={mountRef} className="w-full h-full" />
      <div className="absolute top-4 right-4 bg-gray-900/90 border border-gray-700 rounded-lg p-3 z-10 backdrop-blur-sm">
        <div className="text-xs text-gray-300 mb-2">Units ≈ feet</div>
        <div className="text-xs text-gray-400 mb-2">Dims: 200×85, corners r≈28. Blue ±25 from center, goal lines ±89.</div>
        <div className={`text-xs ${testStatus.includes('failed') ? 'text-red-400' : 'text-green-400'}`}>
          {testStatus}
        </div>
      </div>
      <div className="absolute bottom-4 left-4 bg-gray-900/90 border border-gray-700 rounded-lg p-3 z-10 backdrop-blur-sm">
        <div className="text-xs text-gray-300 mb-1">Controls:</div>
        <div className="text-xs text-gray-400 space-y-1">
          <div>• Drag to orbit</div>
          <div>• Wheel to zoom</div>
          <div>• Click ice to pivot</div>
        </div>
      </div>
    </div>
  )
}
