import { parseRealtimeMessage, type RealtimeMessage } from './realtime.js'

type Status = 'idle' | 'connecting' | 'open' | 'closed'

export class WebsocketClient {
  private ws: WebSocket | null = null
  private onMessageCb: ((msg: RealtimeMessage) => void) | null = null
  private onErrorCb: ((err: unknown) => void) | null = null
  private onStatusCb: ((s: Status) => void) | null = null

  get readyState(): number | null {
    return this.ws?.readyState ?? null
  }

  onMessage(cb: (msg: RealtimeMessage) => void) {
    this.onMessageCb = cb
  }
  onError(cb: (err: unknown) => void) {
    this.onErrorCb = cb
  }
  onStatus(cb: (s: Status) => void) {
    this.onStatusCb = cb
  }

  private setStatus(s: Status) {
    this.onStatusCb?.(s)
  }

  async connect(url: string): Promise<void> {
    await this.disconnect()
    this.setStatus('connecting')
    return new Promise((resolve, reject) => {
      try {
        const ws = new WebSocket(url)
        this.ws = ws
        ws.onopen = () => {
          console.debug(`[WS ${new Date().toISOString()}] open -> ${url}`)
          this.setStatus('open')
          resolve()
        }
        ws.onclose = () => {
          console.debug(`[WS ${new Date().toISOString()}] close`)
          this.setStatus('closed')
        }
        ws.onerror = (e) => {
          console.debug(`[WS ${new Date().toISOString()}] error`, e)
          this.onErrorCb?.(e)
        }
        ws.onmessage = (ev) => {
          const data = typeof ev.data === 'string' ? ev.data : null
          if (!data) return
          // Log raw incoming message (truncate if huge)
          const preview = data.length > 2000 ? data.slice(0, 2000) + '…' : data
          console.debug(`[WS ${new Date().toISOString()}] <= ${preview}`)
          const msg = parseRealtimeMessage(data)
          if (msg) {
            try {
              // Also log parsed type for quick scanning
              // Avoid logging entire object again to limit noise
              const t = (msg as any)?.type ?? 'unknown'
              console.debug(`[WS ${new Date().toISOString()}] parsed type: ${t}`)
            } catch {}
            this.onMessageCb?.(msg)
          }
        }
      } catch (e) {
        this.setStatus('closed')
        reject(e)
      }
    })
  }

  async disconnect(): Promise<void> {
    if (this.ws) {
      try {
        this.ws.close()
      } catch {}
      this.ws = null
      this.setStatus('closed')
    }
  }

  async send(obj: unknown): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error('WebSocket not open')
    this.ws.send(JSON.stringify(obj))
  }

  async sendWithThrottle(obj: unknown): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) throw new Error('WebSocket not open')
    this.ws.send(JSON.stringify(obj))
    while (this.ws.bufferedAmount > 2_000_000) {
      await new Promise((r) => setTimeout(r, 10))
    }
  }
}
