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

// WebSocket connection options interface
export interface WebSocketOptions {
  onTranscription: (transcript: string) => void;
  onBotStartSpeaking: () => void;
  onBotStopSpeaking: () => void;
  onError: (error: Error | string) => void;
  messageManager: MessageManager;
}

// Check if WebSocket is connected
export function isWebSocketConnected(): boolean {
  return socket !== null && socket.readyState === WebSocket.OPEN;
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
      options.onError('WebSocket error occurred');
    };
  } catch (error) {
    console.error('Error connecting to WebSocket:', error);
    options.onError(error instanceof Error ? error : new Error(String(error)));
  }
}

// Disconnect WebSocket
export async function disconnectWebSocket(): Promise<void> {
  cleanupAudioResources();

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
      options.onBotStopSpeaking();
      break;

    case 'response.audio_bytes':
      // Bot is sending audio (meaning it is speaking)
      if (!options.messageManager.isWaitingForBotResponse) {
        options.onBotStartSpeaking();
        options.messageManager.setWaitingForBot();
      }
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
