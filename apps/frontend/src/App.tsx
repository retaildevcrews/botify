import { useState, useRef, useEffect } from 'react';
import { flushSync } from 'react-dom';
import './App.css';
import ChatContainer from './components/ChatContainer/ChatContainer';
import SettingsDrawer from './components/SettingsDrawer/SettingsDrawer';
import { processUserInput } from './services/messageService';
import { useMessageManager } from './hooks/useMessageManager';
import { AppProvider, useAppContext } from './context/AppContext';
import { connectWebSocket, disconnectWebSocket, WebSocketOptions } from './services/websocketService';

const AppContent = () => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isBotSpeaking, setIsBotSpeaking] = useState(false);
  const [isHandsFreeMode, setIsHandsFreeMode] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const { useStreaming, useTextToSpeech, setUseTextToSpeech, sessionId } = useAppContext();
  const messageManager = useMessageManager();

  const {
    messages,
    isWaitingForBotResponse,
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot,
    isStreamComplete,
    setStreamComplete
  } = messageManager;


  // Handle hands-free mode toggle
  const handleHandsFreeToggle = async () => {
    const newMode = !isHandsFreeMode;
    setIsHandsFreeMode(newMode);

    // Connect WebSocket when hands-free mode is turned on
    if (newMode) {
      try {
        const options: WebSocketOptions = {
          onTranscription: handleTranscription,
          onBotStartSpeaking: () => setIsBotSpeaking(true),
          onBotStopSpeaking: () => setIsBotSpeaking(false),
          onError: handleWebSocketError,
          messageManager,
          setIsListening,
        };
        await connectWebSocket(options);
      } catch (error) {
        console.error('Failed to initialize hands-free mode:', error);
        setIsHandsFreeMode(false);
      }
    } else {
      await disconnectWebSocket();
      setIsListening(false);
      setIsBotSpeaking(false);
      resetWaitingStates();
    }
  };

  // Handle speech transcription from WebSocket
  const handleTranscription = (transcript: string) => {
    if (!transcript || !transcript.trim()) {
      return;
    }

    // Add user message with the transcription text
    const userMessage = {
      role: 'user',
      content: transcript.trim()
    };

    messageManager.addUserMessage(userMessage);
    messageManager.setWaitingForBot();
    messageManager.setStreamComplete(false);
  };

  // Handle WebSocket errors
  const handleWebSocketError = (error: Error | string) => {
    const errorText = typeof error === 'string' ? error : error.message;
    setErrorMessage(errorText);
    setIsHandsFreeMode(false);
    disconnectWebSocket().catch(console.error);

    // Clear error message after 5 seconds
    setTimeout(() => {
      setErrorMessage(null);
    }, 5000);
  };

  // Close WebSocket connection when component unmounts
  useEffect(() => {
    return () => {
      disconnectWebSocket().catch(console.error);
    };
  }, []);

  // Listen for speech service errors
  useEffect(() => {
    const handleSpeechError = (event: CustomEvent<string>) => {
      setErrorMessage(event.detail);

      // Clear error message after 5 seconds
      setTimeout(() => {
        setErrorMessage(null);
      }, 5000);
    };

    // Add event listener for speech service errors
    document.addEventListener('speech-service-error', handleSpeechError as EventListener);

    // Clean up
    return () => {
      document.removeEventListener('speech-service-error', handleSpeechError as EventListener);
      disconnectWebSocket().catch(console.error);
    };
  }, []);

  const sendMessage = () => {
    if (!input.trim()) return;

    const currentInput = input;

    // Note: The InputContainer component now handles clearing the textarea
    // when Enter is pressed, but we still need to clear it here for the Send button
    setInput(''); // Clear input for when the send button is clicked

    // Make the API call non-blocking for better responsiveness
    processUserInput(
      currentInput,
      useStreaming,
      messageManager,
      useTextToSpeech,
      sessionId,
      setIsListening
    ).catch(error => {
      console.error('Error processing message:', error);
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();

      // Get the current input value directly from the event target for immediacy
      const currentInput = (e.target as HTMLTextAreaElement).value.trim();

      // Only proceed if there's actual input
      if (!currentInput) return;

      // Clear input field immediately
      flushSync(() => {
        setInput('');
      });

      // Process the message with the captured value
      processUserInput(
        currentInput,
        useStreaming,
        messageManager,
        useTextToSpeech,
        sessionId,
        setIsListening
      ).catch(error => {
        console.error('Error processing message:', error);
      });
    }
  };

  // Process speech result using the shared message processing function
  const processSpeechResult = async (transcriptText: string) => {
    if (!transcriptText.trim()) return;

    await processUserInput(
      transcriptText,
      useStreaming,
      messageManager,
      true, // Force speech enabled for microphone input
      sessionId,
      setIsListening
    );
  };

  const handleMicrophoneClick = async () => {
    try {
      const speechService = await import('./services/speechService');

      if (isListening) {
        const partialTranscript = await speechService.stopSpeechRecognition();
        setIsListening(false);

        if (partialTranscript?.trim()) {
          await processSpeechResult(partialTranscript.trim());
        }
        return;
      }

      setIsListening(true);

      // Automatically enable speech when using microphone input
      if (!useTextToSpeech) {
        setUseTextToSpeech(true);
      }

      try {
        const transcript = await speechService.startSpeechRecognition();
        // Turn off listening state immediately after speech recognition completes
        setIsListening(false);

        if (transcript?.trim()) {
          // Process the transcript without keeping the microphone in listening state
          await processSpeechResult(transcript.trim());
        }
      } catch (error) {
        console.error('Speech recognition failed:', error);
        setIsListening(false);
      }
    } catch (error) {
      console.error('Error in microphone handling:', error);
      setIsListening(false);
    }
  };

  return (
    <div className="root-container">
      <div className="header">
        <div>Botify</div>
        <div className="toggle-container">
          <SettingsDrawer />
        </div>
      </div>
      {errorMessage && (
        <div className="error-notification">
          <p>{errorMessage}</p>
          <button onClick={() => setErrorMessage(null)}>✕</button>
        </div>
      )}
      <ChatContainer
        messages={messages}
        input={input}
        setInput={setInput}
        handleKeyPress={handleKeyPress}
        sendMessage={sendMessage}
        handleMicrophoneClick={handleMicrophoneClick}
        isWaitingForBotResponse={isWaitingForBotResponse}
        isListening={isListening}
        isStreamComplete={isStreamComplete}
        isBotSpeaking={isBotSpeaking}
        isHandsFreeMode={isHandsFreeMode}
        onHandsFreeToggle={handleHandsFreeToggle}
      />
    </div>
  );
};


const App = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
