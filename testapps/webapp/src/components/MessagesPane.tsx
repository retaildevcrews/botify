import { useState, useMemo, useEffect } from 'react'
import type { MessageEntry, OrderItem } from '../hooks/useRealtimeMessages.js'

type Props = {
  entries: MessageEntry[]
  onClearCurrent?: () => void
  canClear?: boolean
}

export function MessagesPane({ entries, onClearCurrent, canClear = true }: Props) {
  // Persist showAll toggle in localStorage
  const [showAll, setShowAll] = useState<boolean>(() => {
    try {
      const raw = localStorage.getItem('messages.showAll')
      if (raw === 'true') return true
      if (raw === 'false') return false
    } catch {}
    return false
  })
  useEffect(() => {
    try { localStorage.setItem('messages.showAll', String(showAll)) } catch {}
  }, [showAll])
  const assistantEntries = useMemo(() => entries.filter((e) => e.role === 'assistant'), [entries])
  const displayEntries = showAll ? assistantEntries : assistantEntries.slice(-1)
  const hasHistory = assistantEntries.length > 1

  return (
    <div className="min-h-0 overflow-auto rounded border border-zinc-200 dark:border-zinc-800 p-3 flex flex-col gap-2">
      <div className="flex items-start justify-end gap-2">
        {hasHistory && (
          <button
            className="text-xs text-zinc-500 underline hover:text-zinc-700 dark:hover:text-zinc-300"
            onClick={() => setShowAll((s) => !s)}
            aria-pressed={showAll}
          >
            {showAll ? 'Show latest only' : `Show all (${assistantEntries.length})`}
          </button>
        )}
      </div>
      {assistantEntries.length === 0 && (
        <div className="message-info">No messages yet. Start recording and stop to request a response.</div>
      )}
      {displayEntries.map((e) => {
        const cls = 'message-assistant'
        const levelCls = e.level === 'error' ? 'message-error' : e.level === 'warning' ? 'message-warning' : ''
        if (e.items && e.items.length > 0) {
          return (
            <div key={e.id} className={`${cls} ${levelCls} space-y-2`}>
              <div className="text-xs font-semibold uppercase tracking-wide text-zinc-500 dark:text-zinc-400">Order Cart</div>
              {e.items.map((item: OrderItem, idx: number) => {
                const qty = item.quantity ?? 1
                const size = item.size ? `${item.size} ` : ''
                const baseLine = `${qty}× ${size}${item.name}`.trim()
                const hasOptions = Array.isArray(item.options) && item.options.length > 0
                const optionsLine = hasOptions
                  ? item.options!
                      .map((o) => {
                        const parts: string[] = []
                        if (o.quantity && o.quantity !== 1) parts.push(`${o.quantity}x`)
                        if (o.amount) parts.push(o.amount)
                        parts.push(o.name)
                        return parts.join(' ')
                      })
                      .join(', ')
                  : ''
                return (
                  <div key={idx} className="flex flex-col">
                    <div>{baseLine}</div>
                    {hasOptions && (
                      <div className="text-xs text-zinc-500 dark:text-zinc-400 ml-4 list-disc">
                        {optionsLine}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )
        }
        return (
          <div key={e.id} className={`${cls} ${levelCls} ${e.isCurrent ? 'current' : ''}`}>
            {e.text}
          </div>
        )
      })}
      {onClearCurrent && (
        <div className="flex items-center gap-3">
          <button
            className="mt-2 text-xs text-zinc-500 underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed"
            disabled={!canClear}
            aria-disabled={!canClear}
            title={!canClear ? 'Stop recording before clearing messages' : undefined}
            onClick={onClearCurrent}
          >
            Clear messages
          </button>
          {hasHistory && !showAll && (
            <span className="mt-2 text-[10px] text-zinc-400" aria-label="History hidden">History hidden</span>
          )}
        </div>
      )}
    </div>
  )
}
