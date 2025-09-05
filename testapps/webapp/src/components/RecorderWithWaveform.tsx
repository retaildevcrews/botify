import { useEffect, useRef } from 'react'

type Props = {
  status: 'idle' | 'recording' | 'paused'
  onStart: () => Promise<void> | void
  onPauseResume: () => Promise<void> | void
  onStop: () => Promise<void> | void
  onDisconnect?: () => Promise<void> | void
  onError?: (message: string) => void
  // Optional provider for real-time waveform bytes (Uint8Array time-domain data from AnalyserNode)
  getWaveformData?: () => Uint8Array | null
  // Whether the Start button should be enabled (e.g., only when WS is connected)
  canStart?: boolean
  // Whether to show a Disconnect button next to Stop (only when connected)
  showDisconnect?: boolean
}

export function RecorderWithWaveform({ status, onStart, onPauseResume, onStop, onDisconnect, onError, getWaveformData, canStart = true, showDisconnect = false }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const animationRef = useRef<number | null>(null)

  // Draw: flat line when not recording; animated wave when recording
  useEffect(() => {
    const base = canvasRef.current
    if (!base) return
    const ctx = base.getContext('2d')!
    let t = 0
    function draw() {
      const canvas = canvasRef.current
      if (!canvas) return
  const w = canvas.width
  const h = canvas.height
      ctx.clearRect(0, 0, w, h)
  ctx.strokeStyle = '#00704A'
  const dpr = window.devicePixelRatio || 1
  ctx.lineWidth = Math.max(1, dpr)
      ctx.beginPath()
      const isActive = status === 'recording' || status === 'paused'
      const data = getWaveformData?.()
      if (isActive && data && data.length > 0) {
        // Render time-domain byte data [0..255]
        const step = data.length / w
        for (let x = 0; x < w; x++) {
          const v = data[Math.min(data.length - 1, Math.floor(x * step))]
          const y = (v / 255) * h
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
      } else if (status === 'recording') {
        // Fallback animated sine when analyser not available
        for (let x = 0; x < w; x++) {
          const y = h / 2 + Math.sin((x + t) * 0.05) * 20
          if (x === 0) ctx.moveTo(x, y)
          else ctx.lineTo(x, y)
        }
        ctx.stroke()
        t += 2
      } else {
        // flat center line
        ctx.moveTo(0, h / 2)
        ctx.lineTo(w, h / 2)
        ctx.stroke()
      }
      animationRef.current = requestAnimationFrame(draw)
    }
    animationRef.current = requestAnimationFrame(draw)
    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current)
    }
  }, [status, getWaveformData])

  // Resize canvas to match CSS size and device pixel ratio for crisp rendering
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const resize = () => {
      const dpr = window.devicePixelRatio || 1
      const cssWidth = Math.max(1, canvas.clientWidth || 320)
      const cssHeight = Math.max(1, canvas.clientHeight || 64)
      const nextW = Math.floor(cssWidth * dpr)
      const nextH = Math.floor(cssHeight * dpr)
      if (canvas.width !== nextW) canvas.width = nextW
      if (canvas.height !== nextH) canvas.height = nextH
    }
    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  return (
    <div className="flex flex-col gap-2">
      {!canStart && (
        <div className="text-sm text-red-600" role="alert">
          You must connect to the WebSocket before starting listening.
        </div>
      )}
      <div className="flex flex-col md:flex-row md:items-center gap-3">
  <div className="flex gap-2">
          {status === 'idle' ? (
          <button
            className="px-3 py-1 rounded bg-primary text-white disabled:opacity-50 disabled:cursor-not-allowed"
            disabled={!canStart}
            aria-disabled={!canStart}
            onClick={async () => {
              try { await onStart() } catch (e: any) { onError?.(e?.message || 'Failed to start recording') }
            }}
          >
            Start
          </button>
          ) : (
            <button
              className="px-3 py-1 rounded bg-yellow-500 text-white"
              onClick={async () => { try { await onPauseResume() } catch (e: any) { onError?.(e?.message || 'Failed to pause/resume') } }}
            >
              {status === 'paused' ? 'Resume' : 'Pause'}
            </button>
          )}
          <div className="flex gap-2">
            <button
              className="px-3 py-1 rounded bg-zinc-200 dark:bg-zinc-700"
              onClick={async () => { try { await onStop() } catch (e: any) { onError?.(e?.message || 'Failed to stop') } }}
            >
              Stop
            </button>
            {showDisconnect && (
              <button
                className="px-3 py-1 rounded bg-red-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={status !== 'idle'}
                aria-disabled={status !== 'idle'}
                title={status !== 'idle' ? 'Stop recording before disconnecting' : undefined}
                onClick={async () => { if (status !== 'idle') return; try { await onDisconnect?.() } catch (e: any) { onError?.(e?.message || 'Failed to disconnect') } }}
              >
                Disconnect
              </button>
            )}
          </div>
        </div>
        <canvas ref={canvasRef} className="rounded border border-zinc-300 dark:border-zinc-700 bg-white/50 dark:bg-black/20 w-full md:w-[420px] h-16 md:h-20" />
      </div>
    </div>
  )
}
