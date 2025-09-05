import { useEffect, useMemo, useState } from 'react'
import { WebsocketClient } from './utils/websocketClient.js'
import type { RealtimeMessage } from './utils/realtime.js'
import { useRealtimeMessages } from './hooks/useRealtimeMessages.js'
import { useRecorder } from './hooks/useRecorder.js'
// Removed inline connection settings in favor of drawer-only UI
import { SettingsDrawer } from './components/SettingsDrawer.js'
import { RecorderWithWaveform } from './components/RecorderWithWaveform.js'
import { MessagesPane } from './components/MessagesPane.js'

export default function App() {
  const [host, setHost] = useState(() => localStorage.getItem('ws.host') || 'localhost')
  const [port, setPort] = useState(() => localStorage.getItem('ws.port') || '8000')
  const [path, setPath] = useState(() => localStorage.getItem('ws.path') || '/realtime')
  const wsUrl = useMemo(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${host}:${port}${path}`
  }, [host, port, path])

  const ws = useMemo(() => new WebsocketClient(), [])
  const { entries, handleMessage, clearAll } = useRealtimeMessages()
  const { start, stop, pauseOrResume, status: recStatus, getWaveformData, getBufferedMillis } = useRecorder({
    onAudioChunk: async (b64: string) => {
      // send with backpressure awareness
      await ws.sendWithThrottle({ type: 'input_audio_buffer.append', audio: b64 })
    },
  })

  const [connected, setConnected] = useState(false)
  const [connecting, setConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  useEffect(() => {
    ws.onMessage((msg: RealtimeMessage) => {
      handleMessage(msg)
    })
    ws.onError((e: unknown) => {
      // Provide a friendly, actionable error for connection problems
      const raw = typeof e === 'string' ? e : (e as any)?.message || 'WebSocket error'
      setError(`Could not connect to the server. Check your settings (gear icon) and try again. ${raw ? `Details: ${raw}` : ''}`)
    })
    ws.onStatus((s: 'idle' | 'connecting' | 'open' | 'closed') => {
      setConnected(s === 'open')
      if (s === 'closed') {
        setConnecting(false)
      }
    })
  }, [ws, handleMessage])

  const connect = async () => {
    setError(null)
    setConnecting(true)
    try {
      await ws.connect(wsUrl)
    } catch (e: any) {
      const msg = e?.message || 'Failed to connect'
      setError(`Could not connect to the server. Check your settings (gear icon) and try again. Details: ${msg}`)
    } finally {
      setConnecting(false)
    }
  }

  const disconnect = async () => {
    await ws.disconnect()
  }

  return (
    <div className="min-h-screen flex flex-col bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100">
      <header className="relative border-b border-zinc-200 dark:border-zinc-800 p-4">
        <h1 className="text-lg font-semibold">Realtime Webapp</h1>
        <button className="absolute top-4 right-4 p-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800" aria-label="Open settings" onClick={() => setDrawerOpen(true)}>
          <span className="material-symbols-outlined">settings</span>
        </button>
      </header>
      <main className="flex-1 p-4">
        {!connected ? (
          <div className="flex flex-col items-start gap-3">
            <p className="text-sm text-zinc-600 dark:text-zinc-300 max-w-prose">
              You must connect to the realtime api before being able to capture orders.
            </p>
            {error && (
              <div className="text-sm text-red-600" role="alert">
                {error}
              </div>
            )}
            <button className="px-3 py-1 rounded bg-primary text-white disabled:opacity-50" disabled={connecting} onClick={connect}>
              {connecting ? 'Connecting…' : 'Connect'}
            </button>
          </div>
        ) : (
          <div className="flex flex-col gap-3 md:flex-row md:items-start md:gap-4">
            <RecorderWithWaveform status={recStatus} canStart={connected} showDisconnect onDisconnect={disconnect} getWaveformData={getWaveformData} onStart={async () => {
            try {
              await start()
            } catch (e: any) {
              setError(e?.message || 'Microphone access failed')
            }
          }} onPauseResume={pauseOrResume} onStop={async () => {
            const ms = getBufferedMillis()
            await stop()
            if (connected) {
              if (ms >= 100) {
                await ws.send({ type: 'input_audio_buffer.commit' })
                await ws.send({ type: 'response.create' })
              } else {
                setError('Not enough audio captured to commit (need at least 100ms). Please try again.')
                // Optionally clear any partial buffer on server side if supported
              }
            }
          }} onError={(msg: string) => setError(msg)} />
            {error && <div className="text-sm text-red-600">{error}</div>}
          </div>
        )}
  {connected && <MessagesPane entries={entries} onClearCurrent={clearAll} canClear={recStatus === 'idle'} />}
      </main>
      <SettingsDrawer
        open={drawerOpen}
        initialHost={host}
        initialPort={port}
        initialPath={path}
        onApply={(newHost, newPort, newPath) => {
          const defaults = { host: 'localhost', port: '8000', path: '/realtime' }
          setHost(newHost)
          setPort(newPort)
          setPath(newPath)
          // Persist only when different from defaults; otherwise clear
          if (newHost !== defaults.host) localStorage.setItem('ws.host', newHost); else localStorage.removeItem('ws.host')
          if (newPort !== defaults.port) localStorage.setItem('ws.port', newPort); else localStorage.removeItem('ws.port')
          if (newPath !== defaults.path) localStorage.setItem('ws.path', newPath); else localStorage.removeItem('ws.path')
        }}
        onClose={() => setDrawerOpen(false)}
      />
    </div>
  )
}
