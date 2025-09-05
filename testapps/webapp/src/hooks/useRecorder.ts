import { useCallback, useMemo, useRef, useState } from 'react'

type Options = {
  onAudioChunk: (b64: string) => Promise<void> | void
}

type Status = 'idle' | 'recording' | 'paused'

export function useRecorder(opts: Options) {
  const [status, setStatus] = useState<Status>('idle')
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const audioCtxRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const pausedRef = useRef<boolean>(false)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const waveformBufRef = useRef<Uint8Array<ArrayBuffer> | null>(null)
  const sampleRateRef = useRef<number>(24000)
  const bufferedSamplesRef = useRef<number>(0)

  const start = useCallback(async () => {
    if (status === 'recording') return
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch (e: any) {
      throw new Error(e?.message || 'Microphone permission denied')
    }
    mediaStreamRef.current = stream

    // Real-time path: AudioContext + ScriptProcessor to push PCM16 frames immediately
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)({ sampleRate: 24000 })
      audioCtxRef.current = audioCtx
      sampleRateRef.current = audioCtx.sampleRate || 24000
      bufferedSamplesRef.current = 0
      const source = audioCtx.createMediaStreamSource(stream)
      sourceRef.current = source
      // Create analyser for real waveform visualization
      const analyser = audioCtx.createAnalyser()
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.85
      analyserRef.current = analyser
      source.connect(analyser)
      const processor = audioCtx.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor
      pausedRef.current = false
      // Split: source feeds processor for PCM and analyser for visualization
      source.connect(processor)
      // Keep graph alive without audible output
      const silent = audioCtx.createGain()
      silent.gain.value = 0
      processor.connect(silent)
      silent.connect(audioCtx.destination)
      processor.onaudioprocess = async (e) => {
        if (pausedRef.current) return
        const input = e.inputBuffer.getChannelData(0)
        // Convert Float32 [-1,1] -> PCM16 Int16Array
        const pcm16 = float32ToPCM16(input)
        bufferedSamplesRef.current += pcm16.length
        const b64 = uint8ToBase64(new Uint8Array(pcm16.buffer))
        await opts.onAudioChunk(b64)
      }
    } catch {
      // Fallback: MediaRecorder path (less real-time). Kept for browser compatibility.
      let mime = 'audio/webm;codecs=opus'
      if (!MediaRecorder.isTypeSupported(mime)) {
        mime = 'audio/webm'
      }
      const mr = new MediaRecorder(stream, { mimeType: mime })
  chunksRef.current = []
  sampleRateRef.current = 24000
  bufferedSamplesRef.current = 0
      // Even in fallback mode, set up an analyser for waveform (no audible output)
      try {
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)()
        audioCtxRef.current = audioCtx
        const source = audioCtx.createMediaStreamSource(stream)
        sourceRef.current = source
        const analyser = audioCtx.createAnalyser()
        analyser.fftSize = 2048
        analyser.smoothingTimeConstant = 0.85
        analyserRef.current = analyser
        const silent = audioCtx.createGain()
        silent.gain.value = 0
        source.connect(analyser)
        analyser.connect(silent)
        silent.connect(audioCtx.destination)
      } catch {}
      mr.ondataavailable = async (ev) => {
        if (ev.data && ev.data.size > 0) {
          chunksRef.current.push(ev.data)
          try {
            const { b64, sampleCount } = await blobToPcm16(ev.data)
            bufferedSamplesRef.current += sampleCount
            await opts.onAudioChunk(b64)
          } catch {}
        }
      }
      mr.start(200)
      mediaRecorderRef.current = mr
    }

    setStatus('recording')
  }, [status, opts])

  const pauseOrResume = useCallback(async () => {
    // Toggle pause flag for ScriptProcessor path
    if (audioCtxRef.current) {
      pausedRef.current = !pausedRef.current
      setStatus(pausedRef.current ? 'paused' : 'recording')
      return
    }
    // Fallback for MediaRecorder path
    const mr = mediaRecorderRef.current
    if (!mr) return
    if (mr.state === 'recording') {
      mr.pause()
      setStatus('paused')
    } else if (mr.state === 'paused') {
      mr.resume()
      setStatus('recording')
    }
  }, [])

  const stop = useCallback(async () => {
    // Clean up AudioContext path
    try {
      const processor = processorRef.current
      const source = sourceRef.current
      if (processor && source) {
        try { processor.disconnect() } catch {}
        try { source.disconnect() } catch {}
      }
      processorRef.current = null
      sourceRef.current = null
      analyserRef.current = null
      waveformBufRef.current = null
      if (audioCtxRef.current) {
        try { await audioCtxRef.current.close() } catch {}
        audioCtxRef.current = null
      }
    } catch {}
    // Clean up MediaRecorder path
    const mr = mediaRecorderRef.current
    if (mr && mr.state !== 'inactive') {
      mr.stop()
    }
    mediaRecorderRef.current = null
    if (mediaStreamRef.current) {
      for (const t of mediaStreamRef.current.getTracks()) t.stop()
      mediaStreamRef.current = null
    }
    // Reset counters
    bufferedSamplesRef.current = 0
    setStatus('idle')
  }, [])

  const getWaveformData = useCallback((): Uint8Array | null => {
    const analyser = analyserRef.current
    if (!analyser) return null
    const needed = analyser.fftSize
    if (!waveformBufRef.current || waveformBufRef.current.length !== needed) {
      // Allocate using length so underlying buffer is ArrayBuffer (not SharedArrayBuffer)
      waveformBufRef.current = new Uint8Array(needed)
    }
    analyser.getByteTimeDomainData(waveformBufRef.current)
    return waveformBufRef.current
  }, [])

  const getBufferedMillis = useCallback((): number => {
    const sr = sampleRateRef.current || 24000
    return (bufferedSamplesRef.current / sr) * 1000
  }, [])

  return useMemo(() => ({ start, pauseOrResume, stop, status, getWaveformData, getBufferedMillis }), [start, pauseOrResume, stop, status, getWaveformData, getBufferedMillis])
}

async function blobToPcm16(blob: Blob): Promise<{ b64: string; sampleCount: number }> {
  const arrayBuffer = await blob.arrayBuffer()
  const audioCtx = new AudioContext()
  const decoded = await audioCtx.decodeAudioData(arrayBuffer.slice(0))
  try { await audioCtx.close() } catch {}

  const targetRate = 24000
  const offline = new OfflineAudioContext(1, Math.ceil(decoded.duration * targetRate), targetRate)
  const src = offline.createBufferSource()
  src.buffer = decoded
  src.connect(offline.destination)
  src.start()
  const rendered = await offline.startRendering()
  const mono = rendered.getChannelData(0)
  const pcm16 = float32ToPCM16(mono)
  const u8 = new Uint8Array(pcm16.buffer)
  return { b64: uint8ToBase64(u8), sampleCount: pcm16.length }
}

function float32ToPCM16(float32Array: Float32Array) {
  const out = new Int16Array(float32Array.length)
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]))
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return out
}

function uint8ToBase64(u8: Uint8Array) {
  let binary = ''
  const chunk = 0x8000
  for (let i = 0; i < u8.length; i += chunk) {
    binary += String.fromCharCode.apply(null, Array.from(u8.subarray(i, i + chunk)) as unknown as number[])
  }
  // btoa expects binary string
  return btoa(binary)
}
