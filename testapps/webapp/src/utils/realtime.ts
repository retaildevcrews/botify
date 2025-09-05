// Types for realtime websocket messages used by the UI

export type RealtimeMessage =
  | { type: 'response.text.delta'; delta: string }
  | { type: 'response.output_text.delta'; delta: string }
  | { type: 'response.audio_transcript.delta'; delta: string }
  | { type: 'response.delta'; delta: string }
  | { type: 'response.text.done'; text?: string }
  | { type: 'response.output_text.done' }
  | { type: 'response.audio_transcript.done' }
  | { type: 'response.done' }
  | { type: 'response.completed' }
  | { type: 'conversation.item.input_audio_transcription.completed'; transcript?: string }
  | { type: 'input_audio_buffer.transcription.completed'; transcript?: string }
  | { type: 'input_audio_transcription.completed'; transcript?: string }
  | { type: 'error'; error?: { message?: string; code?: string; type?: string; param?: string; event_id?: string } }
  | { type: string; [k: string]: unknown }

export function parseRealtimeMessage(data: string): RealtimeMessage | null {
  try {
    return JSON.parse(data) as RealtimeMessage
  } catch {
    return null
  }
}
