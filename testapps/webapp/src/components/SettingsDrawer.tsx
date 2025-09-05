import { useEffect, useMemo, useState } from 'react'

type Props = {
  open: boolean
  initialHost: string
  initialPort: string
  initialPath: string
  onApply: (host: string, port: string, path: string) => void
  onClose: () => void
}

export function SettingsDrawer({ open, initialHost, initialPort, initialPath, onApply, onClose }: Props) {
  const [host, setHost] = useState(initialHost)
  const [port, setPort] = useState(initialPort)
  const [path, setPath] = useState(initialPath)

  // Reset form fields when drawer opens with latest values
  useEffect(() => {
    if (open) {
      setHost(initialHost)
      setPort(initialPort)
      setPath(initialPath)
    }
  }, [open, initialHost, initialPort, initialPath])

  const wsUrl = useMemo(() => {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    return `${proto}://${host || 'localhost'}:${port || '8000'}${path || '/realtime'}`
  }, [host, port, path])

  return (
    <div aria-hidden={!open} className={`fixed inset-0 z-40 ${open ? '' : 'pointer-events-none'}`}>
      {/* Overlay */}
      <div
        className={`absolute inset-0 bg-black/40 transition-opacity ${open ? 'opacity-100' : 'opacity-0'}`}
        onClick={onClose}
        onKeyDown={(e) => { if (e.key === 'Escape') onClose() }}
        aria-hidden
      />

      {/* Panel */}
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Connection Settings"
        className={`absolute right-0 top-0 h-full w-full sm:w-[380px] bg-white dark:bg-zinc-900 shadow-xl border-l border-zinc-200 dark:border-zinc-800 transition-transform ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        <div className="p-4 flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800">
          <h2 className="text-base font-semibold">Connection Settings</h2>
          <button className="p-2 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800" onClick={onClose} aria-label="Close settings">
            <span className="sr-only">Close</span>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
              <path fillRule="evenodd" d="M5.47 5.47a.75.75 0 0 1 1.06 0L12 10.94l5.47-5.47a.75.75 0 1 1 1.06 1.06L13.06 12l5.47 5.47a.75.75 0 1 1-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 0 1-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 0 1 0-1.06Z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="p-4 space-y-4">
          <div className="text-xs text-zinc-500 break-all">{wsUrl}</div>
          <div className="grid grid-cols-1 gap-3">
            <label className="text-sm">
              <div className="text-xs text-zinc-500">Host</div>
              <input className="mt-1 px-2 py-1 border rounded w-full bg-white dark:bg-zinc-800" value={host} onChange={(e) => setHost(e.target.value)} />
            </label>
            <label className="text-sm">
              <div className="text-xs text-zinc-500">Port</div>
              <input className="mt-1 w-28 px-2 py-1 border rounded bg-white dark:bg-zinc-800" value={port} onChange={(e) => setPort(e.target.value)} />
            </label>
            <label className="text-sm">
              <div className="text-xs text-zinc-500">Path</div>
              <input className="mt-1 px-2 py-1 border rounded w-full bg-white dark:bg-zinc-800" value={path} onChange={(e) => setPath(e.target.value)} />
            </label>
          </div>
        </div>
        <div className="mt-auto p-4 border-t border-zinc-200 dark:border-zinc-800 flex justify-end gap-2">
          <button className="px-3 py-1 rounded bg-zinc-200 dark:bg-zinc-700" onClick={onClose}>Cancel</button>
          <button
            className="px-3 py-1 rounded bg-primary text-white"
            onClick={() => {
              onApply(host.trim(), port.trim(), path.trim() || '/')
              onClose()
            }}
          >
            Apply
          </button>
        </div>
      </aside>
    </div>
  )
}
