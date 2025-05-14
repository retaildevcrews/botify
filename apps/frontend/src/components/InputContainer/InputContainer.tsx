import React from 'react';
import './InputContainer.css';

interface InputContainerProps {
  input: string;
  setInput: (value: string) => void;
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendMessage: () => void;
  handleMicrophoneClick: () => void;
}

const InputContainer: React.FC<InputContainerProps> = ({
  input,
  setInput,
  handleKeyPress,
  sendMessage,
  handleMicrophoneClick,
}) => {
  return (
    <div className="input-container">
      <textarea
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder="Type your message..."
        className="input-box"
      />
      <div className="action-bar">
        <button className="icon-button" onClick={handleMicrophoneClick}>
          <span className="material-icons">mic</span>
        </button>
        <button className="icon-button" onClick={sendMessage}>
          <span className="material-icons">send</span>
        </button>
      </div>
    </div>
  );
};

export default InputContainer;
