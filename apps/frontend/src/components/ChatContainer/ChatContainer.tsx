import React, { useEffect, useRef, useState } from 'react';
import './ChatContainer.css';
import InputContainer from '../InputContainer/InputContainer';
import AudioStatusBar from '../AudioStatusBar/AudioStatusBar';
import { Message } from '../../App';
import ReactMarkdown from 'react-markdown';

interface ChatContainerProps {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendMessage: () => void;
  handleMicrophoneClick: () => void;
  isWaitingForBotResponse: boolean;
  isListening?: boolean;
  isStreamComplete?: boolean;
  isBotSpeaking?: boolean;
}

const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  input,
  setInput,
  handleKeyPress,
  sendMessage,
  handleMicrophoneClick,
  isWaitingForBotResponse,
  isListening = false,
  isStreamComplete = false,
  isBotSpeaking = false
}) => {
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const lastMessageContent = messages[messages.length - 1]?.inputMessage.content;

  // Add state for hands-free mode
  const [isHandsFreeMode, setIsHandsFreeMode] = useState(false);

  // Add handler for toggling hands-free mode
  const handleHandsFreeToggle = () => {
    setIsHandsFreeMode(prevMode => !prevMode);
  };

  useEffect(() => {
    // Always scroll to the bottom of the messages container when messages or waiting states change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages.length, lastMessageContent, isWaitingForBotResponse]);

  // Determine if we're waiting for the first response or streaming an existing one
  const isWaitingForFirstResponse = isWaitingForBotResponse &&
    (messages.length === 0 || messages[messages.length - 1].inputMessage.role === 'user');

  const isStreamingResponse = isWaitingForBotResponse && !isStreamComplete &&
    messages.length > 0 && messages[messages.length - 1].inputMessage.role === 'ai';

  return (
    <div className="chat-container">
      <div className="messages-container">
        <div className="messages">
          {messages.map((msg, index) => {
            let displayContent = msg.inputMessage.content;
            // Prevent accidental rendering of [object Object] if content is an object or contains [object Object]
            if (typeof displayContent !== 'string') {
              displayContent = '';
            } else if (displayContent.includes('[object Object]')) {
              displayContent = displayContent.replace(/\[object Object\]/g, '');
            }

            // Only show the waiting indicator inside the last AI message if we're streaming it
            const isLastBotMsg = index === messages.length - 1 &&
                                msg.inputMessage.role === 'ai' &&
                                isStreamingResponse;

            return (
              <div
                key={index}
                className={msg.inputMessage.role === 'user' ? 'user-message' : 'bot-message'}
                ref={index === messages.length - 1 ? lastMessageRef : undefined}
              >
                <div className="message-timestamp">
                  {new Date(msg.timestamp).toLocaleString([], { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
                <div className="message-content">
                  <ReactMarkdown>
                    {displayContent}
                  </ReactMarkdown>
                  {isLastBotMsg && (
                    <div className="bot-message waiting-indicator" style={{ marginTop: 8 }}>
                      <span></span>
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
          {/* Only show the standalone indicator when waiting for first response */}
          {isWaitingForFirstResponse && (
            <div className="bot-message waiting-indicator">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Move AudioStatusBar here, between messages and input */}
      <AudioStatusBar
        isUserSpeaking={isListening}
        isBotSpeaking={isBotSpeaking}
        isHandsFreeMode={isHandsFreeMode}
        onHandsFreeToggle={handleHandsFreeToggle}
      />

      <InputContainer
        input={input}
        setInput={setInput}
        handleKeyPress={handleKeyPress}
        sendMessage={sendMessage}
        handleMicrophoneClick={handleMicrophoneClick}
        isListening={isListening}
        isDisabled={isHandsFreeMode} // Add this new prop
      />
    </div>
  );
};

export default ChatContainer;
