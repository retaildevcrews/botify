import { useCallback, useMemo, useReducer } from 'react'
import type { RealtimeMessage } from '../interfaces/realtime.js'

export type OrderOption = { name: string; amount?: string; quantity?: number }
export type OrderItem = { name: string; quantity?: number; size?: string; options?: OrderOption[] }

export type MessageEntry = {
  id: string
  role: 'user' | 'assistant' | 'system'
  text: string
  level?: 'info' | 'error' | 'warning'
  isCurrent?: boolean
  // When an assistant order is structured, original items retained here
  items?: OrderItem[]
}

type State = { entries: MessageEntry[] }

type Action =
  | { type: 'assistant-text-done'; text?: string; items?: OrderItem[] }
  | { type: 'user-transcript'; text: string }
  | { type: 'error'; message: string }
  | { type: 'clear-all' }

function reducer(state: State, action: Action): State {
  switch (action.type) {
    case 'assistant-text-done': {
      const text = action.text ?? ''
      if (text.trim().length === 0) return state
      const newEntry: MessageEntry = { id: crypto.randomUUID(), role: 'assistant', text, items: action.items }
      return { entries: [...state.entries, newEntry] }
    }
    case 'user-transcript': {
      const entries: MessageEntry[] = [...state.entries, { id: crypto.randomUUID(), role: 'user', text: action.text }]
      return { entries }
    }
    case 'error': {
      const entries: MessageEntry[] = [...state.entries, { id: crypto.randomUUID(), role: 'system', text: action.message, level: 'error' }]
      return { entries }
    }
    case 'clear-all': {
      return { entries: [] }
    }
    default:
      return state
  }
}

export function useRealtimeMessages() {
  const [state, dispatch] = useReducer(reducer, { entries: [] as MessageEntry[] })

  const handleMessage = useCallback((msg: RealtimeMessage) => {
    switch (msg.type) {
      case 'response.text.delta':
      case 'response.output_text.delta':
      case 'response.audio_transcript.delta':
      case 'response.delta':
        // Streaming / delta events are ignored – we only surface the final structured payload.
        break
      case 'response.text.done': {
        // Only surface messages with structured content.items
        const anyMsg = msg as any
        const items = anyMsg?.content?.items
        if (Array.isArray(items) && items.length > 0) {
          const summary = items
            .map((it: any) => {
              const qty = it.quantity ?? 1
              const size = it.size ? `${it.size} ` : ''
              return `${qty}× ${size}${it.name}`.trim()
            })
            .join('\n')
          dispatch({ type: 'assistant-text-done', text: summary, items })
        }
        break
      }
      case 'response.output_text.done':
      case 'response.audio_transcript.done':
      case 'response.done':
      case 'response.completed':
        // Ignore other completion events – only the structured response.text.done is surfaced.
        break
      case 'conversation.item.input_audio_transcription.completed':
      case 'input_audio_buffer.transcription.completed':
      case 'input_audio_transcription.completed':
        if ((msg as any).transcript) dispatch({ type: 'user-transcript', text: (msg as any).transcript as string })
        break
      case 'error': {
        const anyErr = (msg as any).error as { message?: string } | undefined
        const err = anyErr?.message || 'Unknown error'
        dispatch({ type: 'error', message: `API Error: ${err}` })
        break
      }
    }
  }, [])

  const clearAll = useCallback(() => dispatch({ type: 'clear-all' }), [])

  return useMemo(() => ({ entries: state.entries, handleMessage, clearAll }), [state.entries, handleMessage, clearAll])
}
