import { describe, expect, it } from 'vitest'
import { useRealtimeMessages } from './useRealtimeMessages.js'
import { renderHook, act } from '@testing-library/react'

describe('useRealtimeMessages', () => {
  it('ignores deltas and only shows text from response.text.done', () => {
    const { result } = renderHook(() => useRealtimeMessages())
    act(() => result.current.handleMessage({ type: 'response.text.delta', delta: 'Hello' } as any))
    act(() => result.current.handleMessage({ type: 'response.text.delta', delta: ' world' } as any))
    // No entries should be present yet because deltas are ignored
    expect(result.current.entries.length).toBe(0)
    act(() => result.current.handleMessage({ type: 'response.text.done', text: 'Hello world' } as any))
    expect(result.current.entries.at(-1)?.text).toBe('Hello world')
  })
})
