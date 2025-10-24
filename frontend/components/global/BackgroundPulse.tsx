"use client"

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react"

type BackgroundPulseProps = {
  gridSize?: number
  lineLengthPx?: number
  durationSec?: number
  className?: string
}

// Renders a single ECG-like pulse on a grid line. The pulse progressively draws
// across one grid square, then repositions to another grid line on iteration.
export default function BackgroundPulse({
  gridSize = 50,
  lineLengthPx = 50,
  durationSec = 6,
  className,
}: BackgroundPulseProps) {
  const [position, setPosition] = useState<{ top: number; left: number }>({ top: 150, left: 200 })
  const prevKeyRef = useRef<string>("")

  const computeRandomAlignedPosition = useCallback(() => {
    const width = typeof window !== "undefined" ? window.innerWidth : 1200
    const height = typeof window !== "undefined" ? window.innerHeight : 800

    const maxRow = Math.max(1, Math.floor(height / gridSize) - 2)
    const maxCol = Math.max(1, Math.floor((width - lineLengthPx) / gridSize) - 2)

    // Avoid the very first and last lines to keep it away from edges
    const row = Math.floor(2 + Math.random() * (maxRow - 2))
    const col = Math.floor(2 + Math.random() * (maxCol - 2))

    const top = row * gridSize
    const left = col * gridSize
    return { top, left, key: `${top}:${left}` }
  }, [gridSize, lineLengthPx])

  const relocate = useCallback(() => {
    let next = computeRandomAlignedPosition()
    // Ensure we don't repeat same location twice in a row
    if (next.key === prevKeyRef.current) {
      next = computeRandomAlignedPosition()
    }
    prevKeyRef.current = next.key
    setPosition({ top: next.top, left: next.left })
  }, [computeRandomAlignedPosition])

  // Initial placement
  useEffect(() => {
    relocate()
    // Reposition on resize to keep alignment
    const onResize = () => relocate()
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [relocate])

  // Inline animation durations synced to CSS keyframes
  const durations = useMemo(
    () => ({
      container: `${durationSec}s`,
      path: `${durationSec}s`,
    }),
    [durationSec]
  )

  return (
    <div className={"heartbeat-pulse-container" + (className ? ` ${className}` : "")}> 
      <div
        className="heartbeat-pulse-line"
        style={{ top: `${position.top}px`, left: `${position.left}px`, animationDuration: durations.container }}
        onAnimationIteration={relocate}
        // Also relocate at the end in case browsers don't fire iteration
        onAnimationEnd={relocate}
      >
        <svg viewBox="0 0 50 30" preserveAspectRatio="xMidYMid meet">
          <path
            d="M0,15 L10,15 L13,5 L16,25 L19,10 L22,15 L50,15"
            style={{ animationDuration: durations.path }}
          />
        </svg>
      </div>
    </div>
  )
}


