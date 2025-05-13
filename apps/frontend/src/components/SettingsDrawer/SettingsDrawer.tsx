import React, { useState, useRef, useEffect } from 'react';
import './SettingsDrawer.css';
import ToggleSwitch from '../ToggleSwitch/ToggleSwitch';
import { useAppContext } from '../../context/AppContext';

const SettingsDrawer: React.FC = () => {
  const { useStreaming, setUseStreaming, useTextToSpeech, setUseTextToSpeech } = useAppContext();
  const [isOpen, setIsOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(() => {
    const stored = localStorage.getItem('darkMode');
    return stored ? JSON.parse(stored) : false;
  });
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!isOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (drawerRef.current && !drawerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode));
    document.documentElement.style.setProperty(
      '--background-color', darkMode ? 'var(--dark-background-color)' : 'var(--light-background-color)'
    );
    document.documentElement.style.setProperty(
      '--text-color', darkMode ? 'var(--dark-text-color)' : 'var(--light-text-color)'
    );
    document.documentElement.style.setProperty(
      '--messages-container', darkMode ? 'var(--dark-messages-container)' : 'var(--light-messages-container)'
    );
    document.documentElement.style.setProperty(
      '--chat-response-background', darkMode ? 'var(--dark-chat-response-background)' : 'var(--light-chat-response-background)'
    );
  }, [darkMode]);

  const toggleDrawer = () => {
    setIsOpen(!isOpen);
  };

  const toggleDarkMode = () => {
    setDarkMode((prev: boolean) => !prev);
  };

  return (
    <div>
      <button className="gear-icon" onClick={toggleDrawer}>
        <span className="material-icons">settings</span>
      </button>
      <div className={`drawer ${isOpen ? 'open' : ''}`} ref={drawerRef}>
        <button className="close-icon" onClick={toggleDrawer}>
          <i className="material-icons">close</i>
        </button>
        <h2>Settings</h2>
        <div className="controls-container">
          <div className="settings-list">
            <div className="settings-item">
              <span className="setting-name">Stream</span>
              <ToggleSwitch
                id="stream-toggle"
                label=""
                checked={useStreaming}
                onChange={setUseStreaming}
              />
            </div>
            <div className="settings-item">
              <span className="setting-name">Dark Mode</span>
              <ToggleSwitch
                id="dark-mode-toggle"
                label=""
                checked={darkMode}
                onChange={toggleDarkMode}
              />
            </div>
            <div className="settings-item">
              <span className="setting-name">Text to Speech</span>
              <ToggleSwitch
                id="text-to-speech-toggle"
                label=""
                checked={useTextToSpeech}
                onChange={setUseTextToSpeech}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsDrawer;
