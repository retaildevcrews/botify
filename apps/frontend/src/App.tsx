import { useState, useRef } from 'react';
import { flushSync } from 'react-dom';
import './App.css';
import ChatContainer from './components/ChatContainer/ChatContainer';
import SettingsDrawer from './components/SettingsDrawer/SettingsDrawer';
import { processUserInput } from './services/messageService';
import { useMessageManager } from './hooks/useMessageManager';
import { AppProvider, useAppContext } from './context/AppContext';

const AppContent = () => {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const { useStreaming, useTextToSpeech } = useAppContext();
  const messageManager = useMessageManager();

  const {
    messages,
    isWaitingForBotResponse,
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot
  } = messageManager;

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
      useTextToSpeech
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
        useTextToSpeech
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
      useTextToSpeech
    );
  };

  const handleMicrophoneClick = async () => {
    try {
      const speechService = await import('./services/speechService');

      if (isListening) {
        console.log('Stopping speech recognition...');
        const partialTranscript = await speechService.stopSpeechRecognition();
        setIsListening(false);

        if (partialTranscript?.trim()) {
          await processSpeechResult(partialTranscript.trim());
        }
        return;
      }

      setIsListening(true);
      console.log('Starting speech recognition...');

      const transcript = await speechService.startSpeechRecognition();

      if (transcript?.trim()) {
        await processSpeechResult(transcript.trim());
      }
    } catch (error) {
      console.error('Speech recognition failed:', error);
    } finally {
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
      <ChatContainer
        messages={messages}
        input={input}
        setInput={setInput}
        handleKeyPress={handleKeyPress}
        sendMessage={sendMessage}
        handleMicrophoneClick={handleMicrophoneClick}
        isWaitingForBotResponse={isWaitingForBotResponse}
        isListening={isListening}
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
