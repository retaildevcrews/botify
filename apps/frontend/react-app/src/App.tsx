import React, { useState, useRef, useEffect } from 'react';
import { BrowserRouter, Switch, Route, Link } from 'react-router-dom';
import Home from './pages/Home';
import Chat from './pages/Chat';
import SingleQuestion from './pages/SingleQuestion';

const App: React.FC = () => {
  const [sidebarWidth, setSidebarWidth] = useState(250);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme) {
      return savedTheme === 'dark';
    }
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });
  const sidebarRef = useRef<HTMLDivElement>(null);
  const resizeHandleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isDarkMode) {
      document.body.classList.add('dark-theme');
      document.body.classList.remove('light-theme');
      localStorage.setItem('theme', 'dark');
    } else {
      document.body.classList.remove('dark-theme');
      document.body.classList.add('light-theme');
      localStorage.setItem('theme', 'light');
    }
  }, [isDarkMode]);

  const handleMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;

      const newWidth = e.clientX;

      if (newWidth >= 200 && newWidth <= 400) {
        setSidebarWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isDragging]);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
  };

  return (
    <BrowserRouter>
      <div className="app-container">
        <div 
          ref={sidebarRef}
          className={`sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}
          style={{ width: isSidebarCollapsed ? '60px' : `${sidebarWidth}px` }}
        >
          <div className="sidebar-header">
            <h1 className={isSidebarCollapsed ? 'collapsed-title' : ''}>
            </h1>
            <div className="sidebar-controls">
              <button className="collapse-btn" onClick={toggleSidebar}>
                {isSidebarCollapsed ? '→' : '←'}
              </button>
            </div>
          </div>
          
          <nav className="sidebar-nav">
            <Link to="/" className={isSidebarCollapsed ? 'collapsed-link' : ''}>
              <span className="nav-icon">🏠</span>
              {!isSidebarCollapsed && <span className="nav-text">Home</span>}
            </Link>
            <Link to="/chat" className={isSidebarCollapsed ? 'collapsed-link' : ''}>
              <span className="nav-icon">💬</span>
              {!isSidebarCollapsed && <span className="nav-text">Chat</span>}
            </Link>
            <Link to="/question" className={isSidebarCollapsed ? 'collapsed-link' : ''}>
              <span className="nav-icon">🔍</span>
              {!isSidebarCollapsed && <span className="nav-text">Q&A Search</span>}
            </Link>
          </nav>
        </div>
        
        <div 
          ref={resizeHandleRef}
          className={`resize-handle ${isSidebarCollapsed ? 'hidden' : ''}`}
          onMouseDown={handleMouseDown}
        />
        
        <div className="main-container">
          <header className="main-header">
            <div className="header-controls">
              <button className="theme-toggle-btn" onClick={toggleTheme} aria-label="Toggle theme">
                {isDarkMode ? '☀️' : '🌙'}
              </button>
            </div>
          </header>
          <main className="main-content">
            <Switch>
              <Route exact path="/" component={Home} />
              <Route path="/chat" component={Chat} />
              <Route path="/question" component={SingleQuestion} />
            </Switch>
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