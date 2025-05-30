import React, { useRef } from 'react';
import './InputContainer.css';

interface InputContainerProps {
  input: string;
  setInput: (value: string) => void;
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendMessage: () => void;
  handleMicrophoneClick: () => void;
  isListening: boolean;
  isHandsFreeMode?: boolean;
}

const InputContainer: React.FC<InputContainerProps> = ({
  input,
  setInput,
  handleKeyPress,
  sendMessage,
  handleMicrophoneClick,
  isListening,
  isHandsFreeMode = false,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Determine if we're actually listening through microphone input (NOT hands-free mode)
  const isListeningFromMic = isListening && !isHandsFreeMode;

  // Enhanced key press handler that can directly clear the textarea
  const handleKeyPressEnhanced = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();

      // Only proceed if there's actual input
      if (!input.trim()) return;

      // Capture the current input
      const currentInput = input.trim();

      // Immediately clear the textarea by directly manipulating the DOM
      if (textareaRef.current) {
        textareaRef.current.value = '';
      }

      // Update React state (will happen after)
      setInput('');

      // Process the captured message
      sendMessage();
    } else {
      // For all other keys, use the original handler
      handleKeyPress(e);
    }
  };

  return (
    <div className={`input-container ${isHandsFreeMode ? 'disabled' : ''}`}>
      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyPressEnhanced}
        placeholder={isListeningFromMic ? "Listening..." : "Type your message..."}
        className="input-box"
        disabled={isHandsFreeMode}
      />
      <div className="action-bar">
        <button
          className={`icon-button ${isListeningFromMic ? 'listening' : ''}`}
          onClick={handleMicrophoneClick}
          disabled={isHandsFreeMode}
        >
          <span className="material-icons">{isListeningFromMic ? 'mic_none' : 'mic'}</span>
        </button>
        <button
          className="icon-button"
          onClick={sendMessage}
          disabled={input === '' || isHandsFreeMode}
        >
          <span className="material-icons">send</span>
        </button>
      </div>
    </div>
  );
};

export default InputContainer;
