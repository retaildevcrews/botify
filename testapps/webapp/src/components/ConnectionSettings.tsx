type Props = {
  host: string
  port: string
  path: string
  wsUrl: string
  setHost: (v: string) => void
  setPort: (v: string) => void
  setPath: (v: string) => void
}

export function ConnectionSettings({ host, port, path, setHost, setPort, setPath, wsUrl }: Props) {
  const update = (k: 'host' | 'port' | 'path', v: string) => {
    if (k === 'host') {
      setHost(v)
      localStorage.setItem('ws.host', v)
    } else if (k === 'port') {
      setPort(v)
      localStorage.setItem('ws.port', v)
    } else {
      setPath(v)
      localStorage.setItem('ws.path', v)
    }
  }
  return (
    <div className="flex flex-wrap items-end gap-2">
      <label className="text-sm">
        <div className="text-xs text-zinc-500">Host</div>
        <input className="px-2 py-1 border rounded bg-white dark:bg-zinc-800 w-40 sm:w-56" value={host} onChange={(e) => update('host', e.target.value)} />
      </label>
      <label className="text-sm">
        <div className="text-xs text-zinc-500">Port</div>
        <input className="w-20 px-2 py-1 border rounded bg-white dark:bg-zinc-800" value={port} onChange={(e) => update('port', e.target.value)} />
      </label>
      <label className="text-sm">
        <div className="text-xs text-zinc-500">Path</div>
        <input className="px-2 py-1 border rounded bg-white dark:bg-zinc-800 w-40 sm:w-56" value={path} onChange={(e) => update('path', e.target.value)} />
      </label>
      <div className="text-xs text-zinc-500 break-all max-w-full">{wsUrl}</div>
    </div>
  )
}
