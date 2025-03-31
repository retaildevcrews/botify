import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import Chat from './pages/Chat';
import SingleQuestion from './pages/SingleQuestion';

const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 400;
const DEFAULT_SIDEBAR_WIDTH = 250;

const App: React.FC = () => {
  const [sidebarWidth, setSidebarWidth] = useState(DEFAULT_SIDEBAR_WIDTH);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    return savedTheme ? savedTheme === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  
  const sidebarRef = useRef<HTMLDivElement>(null);
  const resizeHandleRef = useRef<HTMLButtonElement>(null);

  // Apply theme based on state
  useEffect(() => {
    const bodyClassList = document.body.classList;
    if (isDarkMode) {
      bodyClassList.add('dark-theme');
      bodyClassList.remove('light-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      bodyClassList.remove('dark-theme');
      bodyClassList.add('light-theme');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const handleMouseDown = (e: React.MouseEvent<HTMLButtonElement>): void => {
    e.preventDefault();
    setIsDragging(true);
  };

  // Handle sidebar resizing
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent): void => {
      if (!isDragging) return;

      const newWidth = e.clientX;
      if (newWidth >= MIN_SIDEBAR_WIDTH && newWidth <= MAX_SIDEBAR_WIDTH) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = (): void => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    // Cleanup event listeners
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const toggleSidebar = (): void => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  const toggleTheme = (): void => {
    setIsDarkMode(!isDarkMode);
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        <div 
          ref={sidebarRef}
          className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}
          style={{ width: isSidebarCollapsed ? '60px' : `${sidebarWidth}px` }}
          aria-expanded={!isSidebarCollapsed}
        >
          <div className="sidebar-header">
            <h1 className={isSidebarCollapsed ? 'collapsed-title' : ''}>
              {!isSidebarCollapsed && 'Botify'}
            </h1>
            <div className="sidebar-controls">
              <button 
                className="collapse-btn" 
                onClick={toggleSidebar}
                aria-label={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
              >
                {isSidebarCollapsed ? '→' : '←'}
              </button>
            </div>
          </div>
          
          <nav className="sidebar-nav">
            <Link to="/" className={isSidebarCollapsed ? 'collapsed-link' : ''} aria-label="Home">
              <span className="nav-icon" aria-hidden="true">🏠</span>
              {!isSidebarCollapsed && <span className="nav-text">Home</span>}
            </Link>
            <Link to="/chat" className={isSidebarCollapsed ? 'collapsed-link' : ''} aria-label="Chat">
              <span className="nav-icon" aria-hidden="true">💬</span>
              {!isSidebarCollapsed && <span className="nav-text">Chat</span>}
            </Link>
            <Link to="/question" className={isSidebarCollapsed ? 'collapsed-link' : ''} aria-label="Q&A Search">
              <span className="nav-icon" aria-hidden="true">🔍</span>
              {!isSidebarCollapsed && <span className="nav-text">Q&A Search</span>}
            </Link>
          </nav>
        </div>
        
        <button 
          ref={resizeHandleRef}
          className={`resize-handle ${isSidebarCollapsed ? 'hidden' : ''}`}
          onMouseDown={handleMouseDown}
          aria-label="Resize sidebar"
          tabIndex={0}
        />
        
        <div className="main-container">
          <header className="main-header">
            <div className="header-controls">
              <button 
                className="theme-toggle-btn" 
                onClick={toggleTheme} 
                aria-label={isDarkMode ? "Switch to light mode" : "Switch to dark mode"}
              >
                <span aria-hidden="true">{isDarkMode ? '☀️' : '🌙'}</span>
              </button>
            </div>
          </header>
          <main className="main-content">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/question" element={<SingleQuestion />} />
            </Routes>
          </main>
          <footer className="footer">
            <div className="version-info">
              <span>Front-End Version: React App 0.1.0</span>
            </div>
          </footer>
        </div>
      </div>
    </BrowserRouter>
  );
};

export default App;