import { MessageManager } from '../hooks/useMessageManager';

const backendApiPrefix = import.meta.env.VITE_BACKEND_API_ENDPOINT_PREFIX;

if (!backendApiPrefix) {
  console.error('VITE_BACKEND_API_ENDPOINT_PREFIX is not defined in the environment variables.');
}

// WebSocket related state variables
let socket: WebSocket | null = null;
let isProcessingAudio = false;
let audioContext: AudioContext | null = null;
let mediaStream: MediaStream | null = null;
let audioProcessor: ScriptProcessorNode | null = null;
let audioSource: MediaStreamAudioSourceNode | null = null;

// Audio output related state variables
let outputAudioContext: AudioContext | null = null;
let audioQueue: string[] = [];
let isPlayingAudio = false;
let currentAudioSource: AudioBufferSourceNode | null = null;
let isNewResponse = true;

// WebSocket connection options interface
export interface WebSocketOptions {
  onTranscription: (transcript: string) => void;
  onBotStartSpeaking: () => void;
  onBotStopSpeaking: () => void;
  onError: (error: Error | string) => void;
  messageManager: MessageManager;
  setIsListening: (isListening: boolean) => void;
}

// Check if WebSocket is connected
export function isWebSocketConnected(): boolean {
  return socket !== null && socket.readyState === WebSocket.OPEN;
}

// Initialize audio output context
function initializeAudioOutput(): void {
  if (!outputAudioContext) {
    outputAudioContext = new window.AudioContext({
      sampleRate: 24000
    });
  }
}

// Clear audio queue and stop current playback
function clearAudioPlayback(): void {
  audioQueue = [];
  isPlayingAudio = false;

  try {
    currentAudioSource?.stop();
    currentAudioSource = null;
  } catch (e) {
    // Source might already be stopped
  }
}

// Play audio from base64 PCM16 data
async function playAudioData(base64Audio: string): Promise<void> {
  try {
    if (!outputAudioContext) {
      initializeAudioOutput();
    }

    // Resume audio context if it's suspended (required by browser policies)
    if (outputAudioContext!.state === 'suspended') {
      await outputAudioContext!.resume();
    }

    // Decode base64 to binary
    const binaryString = atob(base64Audio);
    const bytes = new Uint8Array(binaryString.length);
    for (let i = 0; i < binaryString.length; i++) {
      bytes[i] = binaryString.charCodeAt(i);
    }

    // Convert PCM16 to Float32 for Web Audio API
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768; // Convert to [-1, 1] range
    }

    // Create audio buffer
    const audioBuffer = outputAudioContext!.createBuffer(1, float32Array.length, 24000);
    audioBuffer.getChannelData(0).set(float32Array);

    // Create and configure audio source
    const source = outputAudioContext!.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(outputAudioContext!.destination);

    // Track the current source for potential cleanup
    currentAudioSource = source;

    // Return a promise that resolves when the audio finishes playing
    return new Promise((resolve) => {
      source.onended = () => {
        if (currentAudioSource === source) {
          currentAudioSource = null;
        }
        resolve();
      };

      // Play the audio
      source.start();
    });
  } catch (error) {
    console.error('Error playing audio:', error);
    throw error;
  }
}

// Queue-based audio playback for smooth streaming
function queueAudioData(base64Audio: string, onBotStopSpeaking: () => void): void {
  audioQueue.push(base64Audio);
  if (!isPlayingAudio) {
    playNextAudioChunk(onBotStopSpeaking);
  }
}

async function playNextAudioChunk(onBotStopSpeaking: () => void): Promise<void> {
  if (audioQueue.length === 0) {
    isPlayingAudio = false;
    onBotStopSpeaking();
    return;
  }

  isPlayingAudio = true;
  const audioData = audioQueue.shift();

  try {
    // Wait for the current audio chunk to finish before playing the next one
    await playAudioData(audioData!);
    // Immediately play the next chunk without delay to prevent gaps
    playNextAudioChunk(onBotStopSpeaking);
  } catch (error) {
    console.error('Error in audio queue:', error);
    // On error, try the next chunk after a short delay
    setTimeout(() => playNextAudioChunk(onBotStopSpeaking), 100);
  }
}

// Connect to WebSocket for hands-free mode
export async function connectWebSocket(options: WebSocketOptions): Promise<void> {
  if (socket && socket.readyState === WebSocket.OPEN) {
    return;
  }

  try {
    // Clean up any existing connections first
    await disconnectWebSocket();

    // Create new WebSocket connection
    const wsUrl = `${backendApiPrefix.replace(/^http/, 'ws')}/realtime`;
    socket = new WebSocket(wsUrl);

    socket.onopen = async () => {
      try {
        // Request microphone access
        mediaStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1,  // Mono
            sampleRate: 24000 // 24kHz sample rate for OpenAI
          }
        });

        // Setup audio processing
        audioContext = new AudioContext({ sampleRate: 24000 });
        audioSource = audioContext.createMediaStreamSource(mediaStream);
        audioProcessor = audioContext.createScriptProcessor(4096, 1, 1);

        audioSource.connect(audioProcessor);
        audioProcessor.connect(audioContext.destination);

        // Process audio and send it over WebSocket
        audioProcessor.onaudioprocess = function(e) {
          if (socket && socket.readyState === WebSocket.OPEN) {
            const inputBuffer = e.inputBuffer.getChannelData(0);

            // Convert Float32 to Int16 (PCM16)
            const pcm16Buffer = new Int16Array(inputBuffer.length);
            for (let i = 0; i < inputBuffer.length; i++) {
              // Clamp values to [-1, 1] and convert to 16-bit signed integer
              const clampedValue = Math.max(-1, Math.min(1, inputBuffer[i]));
              pcm16Buffer[i] = Math.floor(clampedValue * 32767);
            }

            // Convert to base64
            const base64Data = btoa(String.fromCharCode(...new Uint8Array(pcm16Buffer.buffer)));

            const message = {
              type: 'input_audio_buffer.append',
              audio: base64Data
            };

            socket.send(JSON.stringify(message));
          }
        };

        isProcessingAudio = true;
      } catch (error) {
        console.error('Error accessing microphone:', error);
        options.onError(error instanceof Error ? error : new Error(String(error)));
        disconnectWebSocket();
      }
    };

    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        processWebSocketMessage(message, options);
      } catch (error) {
        console.error('Error processing WebSocket message:', error, event.data);
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      cleanupAudioResources();
      socket = null;
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      options.onError('WebSocket connection error occurred.');
    };
  } catch (error) {
    console.error('Error connecting to WebSocket:', error);
    const errorMessage = error instanceof Error ? error.message : String(error);
    options.onError(`Failed to connect: ${errorMessage}`);
  }
}

// Disconnect WebSocket
export async function disconnectWebSocket(): Promise<void> {
  cleanupAudioResources();
  clearAudioPlayback();

  if (outputAudioContext) {
    try {
      await outputAudioContext.close();
    } catch (e) {
      console.error('Error closing audio output context:', e);
    }
    outputAudioContext = null;
  }

  if (socket) {
    if (socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    socket = null;
  }
}

// Clean up audio resources
function cleanupAudioResources(): void {
  isProcessingAudio = false;

  if (audioProcessor) {
    audioProcessor.disconnect();
    audioProcessor = null;
  }

  if (audioSource) {
    audioSource.disconnect();
    audioSource = null;
  }

  if (audioContext) {
    audioContext.close().catch(console.error);
    audioContext = null;
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
}

// Process WebSocket messages
function processWebSocketMessage(message: any, options: WebSocketOptions): void {
  switch (message.type) {
    case 'conversation.item.input_audio_transcription.completed':
      if (message.transcript) {
        options.onTranscription(message.transcript);
      } else {
        console.warn('Received empty transcription from WebSocket');
      }
      break;

    case 'response.audio_transcript.delta':
      // Handle streaming response
      if (message.delta) {
        options.messageManager.updateOrAddBotMessage(message.delta);
      }
      break;

    case 'response.audio_transcript.done':
      // Bot has finished speaking
      options.messageManager.setStreamComplete(true);
      break;

    case 'response.audio.delta':
      // Handle streaming audio response
      if (message.delta) {
        // Clear any previous audio if this is the start of a new response
        if (isNewResponse) {
          clearAudioPlayback();
          isNewResponse = false;
        }
        queueAudioData(message.delta, options.onBotStopSpeaking);
      }

      // Notify that bot is speaking
      if (!options.messageManager.isWaitingForBotResponse) {
        options.onBotStartSpeaking();
        options.messageManager.setWaitingForBot();
      }
      break;

    // Audio response complete
    case 'response.audio.done':
      isNewResponse = true;
      options.messageManager.setStreamComplete(true);
      break;

    // Bot is sending audio (meaning it is speaking)
    case 'response.audio_bytes':
      if (!options.messageManager.isWaitingForBotResponse) {
        options.onBotStartSpeaking();
        options.messageManager.setWaitingForBot();
      }

      // Play audio if enabled
      queueAudioData(message?.audio, options.onBotStopSpeaking);
      break;

    // User has started speaking
    case 'input_audio_buffer.speech_started':
      clearAudioPlayback();
      options.onBotStopSpeaking();
      options.setIsListening(true);
      break;

    // User has stopped speaking
    case 'input_audio_buffer.speech_stopped':
      options.setIsListening(false);
      break;

    case 'error':
      const errorMsg = message.error?.message || 'Unknown WebSocket error';
      console.error('WebSocket API error:', errorMsg, message);
      options.onError(errorMsg);
      break;

    default:
      console.log(`Unhandled message type: ${message.type}`, message);
      break;
  }
}
