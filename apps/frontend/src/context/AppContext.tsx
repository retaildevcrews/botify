import React, { createContext, useContext, useState, useEffect } from 'react';

interface AppContextType {
  useStreaming: boolean;
  setUseStreaming: (value: boolean) => void;
}

const defaultContextValue: AppContextType = {
  useStreaming: false,
  setUseStreaming: () => {}
};

export const AppContext = createContext<AppContextType>(defaultContextValue);

export const useAppContext = () => useContext(AppContext);

export const AppProvider: React.FC<{children: React.ReactNode}> = ({ children }) => {
  const [useStreaming, setUseStreaming] = useState(() => {
    const stored = localStorage.getItem('useStreaming');
    return stored ? JSON.parse(stored) : false;
  });

  useEffect(() => {
    localStorage.setItem('useStreaming', JSON.stringify(useStreaming));
    console.log(`Streaming mode toggled: ${useStreaming}`);
  }, [useStreaming]);

  return (
    <AppContext.Provider value={{ useStreaming, setUseStreaming }}>
      {children}
    </AppContext.Provider>
  );
};
