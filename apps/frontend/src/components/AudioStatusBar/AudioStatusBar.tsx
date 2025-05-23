import React from 'react';
import './AudioStatusBar.css';

interface AudioStatusBarProps {
  isUserSpeaking: boolean;
  isBotSpeaking: boolean;
  isHandsFreeMode: boolean;
  onHandsFreeToggle: () => void;
}

const AudioStatusBar: React.FC<AudioStatusBarProps> = ({
  isUserSpeaking,
  isBotSpeaking,
  isHandsFreeMode,
  onHandsFreeToggle
}) => {
  return (
    <div className="audio-status-bar">
      <div className={`audio-status-indicator user-audio ${isUserSpeaking ? 'active' : ''}`}>
        <div className="audio-icon">
          <i className="mic-icon"></i>
        </div>
        <span>Audio Input</span>
      </div>

      <div
        className={`hands-free-button ${isHandsFreeMode ? 'active' : ''}`}
        onClick={onHandsFreeToggle}
      >
        Hands-Free
      </div>

      <div className={`audio-status-indicator bot-audio ${isBotSpeaking ? 'active' : ''}`}>
        <span>Audio Output</span>
        <div className="audio-icon">
          <i className="speaker-icon"></i>
        </div>
      </div>
    </div>
  );
};

export default AudioStatusBar;
