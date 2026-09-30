import { useEffect, useRef } from 'react'
import { Application, Container, Graphics } from 'pixi.js'

export interface CityAgent {
  id: string
  x: number
  y: number
  color: number
  energy: number
  fundsLow: boolean
  status: 'alive' | 'dead'
}

const DISTRICTS = [
  { name: 'Housing', x: 0.15, y: 0.2 },
  { name: 'Office', x: 0.5, y: 0.2 },
  { name: 'Studio', x: 0.85, y: 0.2 },
  { name: 'Market', x: 0.15, y: 0.75 },
  { name: 'Bank', x: 0.5, y: 0.75 },
  { name: 'Library', x: 0.85, y: 0.75 },
]

/** PixiJS city map: static district zones + agent dots with energy rings (UIUX S4.1). */
export default function CityCanvas({ agents }: { agents: CityAgent[] }) {
  const hostRef = useRef<HTMLDivElement>(null)
  const appRef = useRef<Application | null>(null)
  const layerRef = useRef<Container | null>(null)

  useEffect(() => {
    const app = new Application()
    appRef.current = app
    let disposed = false
    app.init({ width: 960, height: 540, background: '#0E1116', antialias: true }).then(() => {
      if (disposed || !hostRef.current) {
        void app.destroy()
        return
      }
      hostRef.current.appendChild(app.canvas)
      const layer = new Container()
      layerRef.current = layer
      app.stage.addChild(layer)
      drawDistricts(layer)
    })
    return () => {
      disposed = true
      void appRef.current?.destroy(false, { children: true, texture: true })
      appRef.current = null
    }
  }, [])

  useEffect(() => {
    const layer = layerRef.current
    const app = appRef.current
    if (!layer || !app) return
    layer.removeChildren()
    for (const a of agents) {
      const g = new Graphics()
      const px = a.x * app.renderer.width
      const py = a.y * app.renderer.height
      if (a.status === 'dead') {
        g.rect(px - 5, py - 5, 10, 10).fill(0x9aa7b4)
      } else {
        g.circle(px, py, 7).fill(a.color)
        const energyColor = a.energy > 30 ? 0x3fb950 : 0xd29922
        g.circle(px, py, 11).stroke({ width: 2, color: energyColor })
        if (a.fundsLow) g.circle(px, py, 14).stroke({ width: 2, color: 0xf85149 })
      }
      layer.addChild(g)
    }
  }, [agents])

  return <div ref={hostRef} className="overflow-hidden rounded border border-border" />
}

function drawDistricts(layer: Container): void {
  const bg = new Graphics()
  for (const d of DISTRICTS) {
    const x = d.x * 960
    const y = d.y * 540
    bg.roundRect(x - 110, y - 70, 220, 140, 8)
    bg.stroke({ width: 1, color: 0x2a323d })
    bg.circle(x, y, 3).fill(0x2a323d)
  }
  layer.addChild(bg)
}
