import { useState, useEffect, useCallback, useRef } from 'react';
import './App.css';
import ChatContainer from './components/ChatContainer/ChatContainer';
import SettingsDrawer from './components/SettingsDrawer/SettingsDrawer';
import { sendMessageToBot } from './services/botservice';

export interface InputMessage {
  role: string;
  content: string;
}

export interface Message {
  inputMessage: InputMessage;
  timestamp: string;
}

export interface Input {
  messages: InputMessage[];
}

const App = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [useStreaming, setUseStreaming] = useState(() => {
    const stored = localStorage.getItem('useStreaming');
    return stored ? JSON.parse(stored) : false;
  });
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  // Use this ref to track if we've created a bot message for streaming
  const botMessageCreatedRef = useRef(false);

  const sendMessage = async () => {
    console.log('sendMessage called with input:', input);
    if (!input.trim()) {
      console.log('Input is empty, message not sent');
      return;
    }

    const inputMessage: InputMessage = {
      role: 'user',
      content: input
    };

    const userMessage: Message = {
      inputMessage: inputMessage,
      timestamp: new Date().toISOString()
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');

    setIsWaitingForBotResponse(true);
    botMessageCreatedRef.current = false;

    try {
      console.log('Sending message to API:', input);
      const sessionId = "session-id-placeholder";
      const userId = "user-id-placeholder";

      // Extract all previous inputMessages to create conversation history
      const conversationHistory: InputMessage[] = messages.map(message => message.inputMessage);
      // Add the current user message to the history
      const allMessages: InputMessage[] = [...conversationHistory, inputMessage];

      if (!useStreaming) {
        const response = await sendMessageToBot(allMessages, useStreaming, sessionId, userId);
        if (response) {
          response.timestamp = new Date().toISOString();
          setMessages((prev) => [...prev, response]);
        }
        setIsWaitingForBotResponse(false);
      } else {
        let lastBotMsgIndex: number | null = null;
        await sendMessageToBot(
          allMessages,
          useStreaming,
          sessionId,
          userId,
          (chunk: string) => {
            setIsWaitingForBotResponse(false); // streaming displayResponse done
            setMessages((prev) => {
              const updatedMessages = [...prev];
              // Always append to the last message, which should be our bot message
              if (lastBotMsgIndex === null || updatedMessages[lastBotMsgIndex]?.inputMessage.role !== 'ai') {
                // If no bot message exists, create a new one
                const newBotMessage: Message = {
                  inputMessage: {
                    role: 'ai',
                    content: chunk
                  },
                  timestamp: new Date().toISOString()
                };
                updatedMessages.push(newBotMessage);
                lastBotMsgIndex = updatedMessages.length - 1;
              } else {
                updatedMessages[lastBotMsgIndex] = {
                  ...updatedMessages[lastBotMsgIndex],
                  inputMessage: {
                    ...updatedMessages[lastBotMsgIndex].inputMessage,
                    content: updatedMessages[lastBotMsgIndex].inputMessage.content + chunk
                  }
                };
              }
              return updatedMessages;
            });
          }
        );
      }
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      botMessageCreatedRef.current = false;
    }
  };

  const handleStreamToggle = useCallback(() => {
    console.log(`Streaming mode toggled: ${useStreaming}`);
  }, [useStreaming]);

  useEffect(() => {
    handleStreamToggle();
  }, [handleStreamToggle]);

  useEffect(() => {
    localStorage.setItem('useStreaming', JSON.stringify(useStreaming));
  }, [useStreaming]);

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const handleMicrophoneClick = () => {
    console.log('Microphone button clicked');
  };

  return (
    <div className="root-container">
      <div className="header">
        <div>Botify</div>
        <div className="toggle-container">
          <SettingsDrawer
            useStreaming={useStreaming}
            setUseStreaming={setUseStreaming}
          />
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
      />
    </div>
  );
};

export default App;
