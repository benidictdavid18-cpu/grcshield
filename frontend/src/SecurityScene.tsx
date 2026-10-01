import { useEffect, useRef, useState } from 'react'
import { type RiskSummary } from './api'
import { Reference } from './RecordDrawer'

type Point = [number, number, number]
const COLORS = { LOW: '#54836a', MEDIUM: '#b48b40', HIGH: '#c57a44', CRITICAL: '#b85750' }

/** A small perspective renderer: an extruded shield mesh, orbital paths and live risk nodes.
 * No external assets, GPU dependency or synthetic security telemetry. */
export function SecurityScene({ risks }: { risks: RiskSummary[] }) {
  const canvas = useRef<HTMLCanvasElement>(null)
  const orientation = useRef({ yaw: -0.3, pitch: -0.12 })
  const hitAreas = useRef<{ x: number; y: number; ref: string }[]>([])
  const drag = useRef<{ x: number; y: number; moved: boolean } | null>(null)
  const [selected, select] = useState('')
  const [paused, setPaused] = useState(
    () => window.matchMedia('(prefers-reduced-motion: reduce)').matches,
  )
  const active = risks.find((risk) => risk.risk_ref === selected)

  useEffect(() => {
    const surface = canvas.current
    const ctx = surface?.getContext('2d')
    if (!surface || !ctx) return
    let frame = 0,
      last = 0,
      visible = true
    const observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
    })
    observer.observe(surface)
    const outline: Point[] = [
      [0, -1.15, 0.18],
      [0.82, -0.79, 0.18],
      [0.71, 0.27, 0.18],
      [0.42, 0.78, 0.18],
      [0, 1.04, 0.18],
      [-0.42, 0.78, 0.18],
      [-0.71, 0.27, 0.18],
      [-0.82, -0.79, 0.18],
    ]
    const draw = (time: number) => {
      frame = requestAnimationFrame(draw)
      if (!visible || document.hidden || time - last < 32) return
      const delta = Math.min(time - last, 50)
      last = time
      if (!paused && !drag.current) orientation.current.yaw += delta * 0.000055
      const rect = surface.getBoundingClientRect(),
        width = rect.width,
        height = rect.height
      const ratio = Math.min(window.devicePixelRatio || 1, 2)
      if (
        surface.width !== Math.round(width * ratio) ||
        surface.height !== Math.round(height * ratio)
      ) {
        surface.width = Math.round(width * ratio)
        surface.height = Math.round(height * ratio)
      }
      ctx.setTransform(ratio, 0, 0, ratio, 0, 0)
      ctx.clearRect(0, 0, width, height)
      const dark = document.documentElement.dataset.theme === 'dark'
      const metal = dark
        ? ['#777a79', '#333735', '#555957', '#8b8f8b']
        : ['#c6c5bb', '#72766e', '#9da196', '#e0dfd5']
      const ink = dark ? '#ddd8ca' : '#514f44'
      const yaw = orientation.current.yaw,
        pitch = orientation.current.pitch
      const scale = Math.min(width / 5.4, height / 4.3)
      const project = ([x, y, z]: Point) => {
        const rx = x * Math.cos(yaw) + z * Math.sin(yaw),
          rz = z * Math.cos(yaw) - x * Math.sin(yaw)
        const ry = y * Math.cos(pitch) - rz * Math.sin(pitch),
          depth = y * Math.sin(pitch) + rz * Math.cos(pitch)
        const perspective = 6 / (6 + depth)
        return {
          x: width / 2 + rx * scale * perspective,
          y: height / 2 + ry * scale * perspective,
          z: depth,
          perspective,
        }
      }
      const path = (points: Point[], color: string, fill?: string, lineWidth = 1) => {
        ctx.beginPath()
        points.forEach((point, index) => {
          const p = project(point)
          if (index) ctx.lineTo(p.x, p.y)
          else ctx.moveTo(p.x, p.y)
        })
        if (fill) {
          ctx.closePath()
          ctx.fillStyle = fill
          ctx.fill()
        }
        ctx.strokeStyle = color
        ctx.lineWidth = lineWidth
        ctx.stroke()
      }
      // Ground-plane hexagons establish depth without implying a performance metric.
      for (const radius of [1.05, 1.65, 2.2]) {
        const ring: Point[] = Array.from({ length: 7 }, (_, i) => [
          Math.cos((i / 6) * Math.PI * 2) * radius,
          1.38,
          Math.sin((i / 6) * Math.PI * 2) * radius,
        ])
        path(
          ring,
          radius === 1.65 ? '#9a92725c' : '#9a92722a',
          radius === 1.05 ? '#8a817b18' : undefined,
        )
      }
      for (let ring = 0; ring < 3; ring++) {
        const points: Point[] = Array.from({ length: 81 }, (_, i) => {
          const angle = (i / 80) * Math.PI * 2
          return [
            Math.cos(angle) * (2.1 + ring * 0.08),
            Math.sin(angle * 2) * 0.22 + (ring - 1) * 0.24,
            Math.sin(angle) * (1.8 + ring * 0.08),
          ]
        })
        path(points, ['#9a927262', '#9a927238', '#9a92721f'][ring])
      }
      const faces: { points: Point[]; fill: string }[] = []
      outline.forEach((point, i) => {
        const next = outline[(i + 1) % outline.length]
        faces.push({
          points: [point, next, [next[0], next[1], -0.2], [point[0], point[1], -0.2]],
          fill: i < 3 ? metal[0] : metal[1],
        })
      })
      faces.push({ points: outline.map(([x, y]) => [x, y, -0.2]), fill: metal[2] })
      faces.push({ points: outline, fill: metal[3] })
      faces.sort(
        (a, b) =>
          b.points.reduce((sum, p) => sum + project(p).z, 0) / b.points.length -
          a.points.reduce((sum, p) => sum + project(p).z, 0) / a.points.length,
      )
      ctx.shadowColor = '#29281e22'
      ctx.shadowBlur = 9
      faces.forEach((face) => path(face.points, '#807d6b80', face.fill, 1.2))
      ctx.shadowBlur = 0
      const inner = outline.map(([x, y]) => [x * 0.82, y * 0.82, 0.185] as Point)
      path([...inner, inner[0]], '#f9f5e5b0', undefined, 1.4)
      // Faceted surface and a small geometric core in the shield.
      for (const point of [outline[0], outline[2], outline[4], outline[6]])
        path([[0, -0.1, 0.19], point], '#57574b44')
      const core: Point[] = Array.from({ length: 7 }, (_, i) => [
        Math.cos((i / 6) * Math.PI * 2) * 0.3,
        Math.sin((i / 6) * Math.PI * 2) * 0.3 - 0.12,
        0.2,
      ])
      path(core, '#e8e4d6', metal[1], 2)
      path(
        [
          [0, -0.3, 0.21],
          [0, 0.05, 0.21],
        ],
        '#e8e4d6',
        undefined,
        3,
      )
      const nodes = risks
        .map((risk, i) => {
          const angle = (i / Math.max(risks.length, 1)) * Math.PI * 2
          const point: Point = [
            Math.cos(angle) * 2.1,
            Math.sin(angle * 2) * 0.22 + ((i % 3) - 1) * 0.24,
            Math.sin(angle) * 1.8,
          ]
          return { risk, point, position: project(point) }
        })
        .sort((a, b) => b.position.z - a.position.z)
      hitAreas.current = []
      nodes.forEach(({ risk, point, position: p }) => {
        const highlighted = risk.risk_ref === selected
        const color = COLORS[risk.residual.band]
        ctx.globalAlpha = selected && !highlighted ? 0.35 : p.z > 0.5 ? 0.65 : 1
        if (highlighted) path([point, [0, -0.1, 0.2]], color + '80')
        ctx.beginPath()
        ctx.arc(p.x, p.y, (highlighted ? 7 : 4) * p.perspective, 0, Math.PI * 2)
        ctx.shadowBlur = 0
        ctx.shadowColor = color
        ctx.fillStyle = color
        ctx.fill()
        ctx.shadowBlur = 0
        ctx.beginPath()
        ctx.arc(p.x, p.y, (highlighted ? 12 : 8) * p.perspective, 0, Math.PI * 2)
        ctx.strokeStyle = color + '50'
        ctx.stroke()
        if (highlighted || risks.length <= 8 || p.z < -0.8) {
          ctx.font = '10px ui-monospace, monospace'
          ctx.fillStyle = ink
          ctx.textAlign = 'center'
          ctx.fillText(risk.risk_ref, p.x, p.y - 15)
        }
        hitAreas.current.push({ x: p.x, y: p.y, ref: risk.risk_ref })
      })
      ctx.globalAlpha = 1
    }
    frame = requestAnimationFrame(draw)
    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [risks, paused, selected])

  return (
    <section className="security-scene" aria-label="Interactive three-dimensional risk model">
      <div className="scene-caption">
        <span>
          <i />
          ASSESSMENT MODEL
        </span>
        <span>01 / EXPOSURE MAP</span>
      </div>
      <canvas
        ref={canvas}
        aria-label="Drag to rotate the shield and risk nodes. Use the risk selector below for keyboard access."
        onPointerDown={(event) => {
          drag.current = { x: event.clientX, y: event.clientY, moved: false }
          event.currentTarget.setPointerCapture(event.pointerId)
        }}
        onPointerMove={(event) => {
          if (!drag.current) return
          const dx = event.clientX - drag.current.x,
            dy = event.clientY - drag.current.y
          if (Math.abs(dx) + Math.abs(dy) > 2) drag.current.moved = true
          orientation.current.yaw += dx * 0.008
          orientation.current.pitch = Math.max(
            -0.6,
            Math.min(0.6, orientation.current.pitch + dy * 0.004),
          )
          drag.current.x = event.clientX
          drag.current.y = event.clientY
        }}
        onPointerUp={(event) => {
          if (drag.current && !drag.current.moved) {
            const rect = event.currentTarget.getBoundingClientRect()
            const hit = [...hitAreas.current]
              .reverse()
              .find(
                (point) =>
                  Math.hypot(
                    point.x - (event.clientX - rect.left),
                    point.y - (event.clientY - rect.top),
                  ) < 15,
              )
            if (hit) {
              select(hit.ref)
              setPaused(true)
            }
          }
          drag.current = null
        }}
        onPointerCancel={() => {
          drag.current = null
        }}
      />
      <div className="scene-controls">
        <span>DRAG TO ROTATE · SELECT TO INSPECT</span>
        <button onClick={() => setPaused(!paused)} aria-pressed={paused}>
          {paused ? 'Rotate model' : 'Pause motion'}
        </button>
        <button
          onClick={() => {
            orientation.current = { yaw: -0.3, pitch: -0.12 }
            select('')
          }}
        >
          Reset
        </button>
      </div>
      <div className="scene-selection">
        <label htmlFor="scene-risk">Inspect exposure</label>
        <select
          id="scene-risk"
          value={selected}
          onChange={(event) => {
            select(event.target.value)
            setPaused(true)
          }}
        >
          <option value="">Select a risk node</option>
          {risks.map((risk) => (
            <option key={risk.risk_ref} value={risk.risk_ref}>
              {risk.risk_ref} · {risk.title}
            </option>
          ))}
        </select>
        {active && (
          <div className="scene-risk">
            <Reference value={active.risk_ref} />
            <span>{active.title}</span>
            <span className={`band band-${active.residual.band.toLowerCase()}`}>
              {active.residual.score} · {active.residual.band.toLowerCase()}
            </span>
          </div>
        )}
      </div>
    </section>
  )
}
