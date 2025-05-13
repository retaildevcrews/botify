import React, { createContext, useContext, useState, useEffect } from 'react';

interface AppContextType {
  useStreaming: boolean;
  setUseStreaming: (value: boolean) => void;
  useTextToSpeech: boolean;
  setUseTextToSpeech: (value: boolean) => void;
}

const defaultContextValue: AppContextType = {
  useStreaming: false,
  setUseStreaming: () => {},
  useTextToSpeech: false,
  setUseTextToSpeech: () => {}
};

export const AppContext = createContext<AppContextType>(defaultContextValue);

export const useAppContext = () => useContext(AppContext);

export const AppProvider: React.FC<{children: React.ReactNode}> = ({ children }: {children: React.ReactNode}) => {
  // Default streaming to OFF for better initial experience
  const [useStreaming, setUseStreaming] = useState(() => {
    const stored = localStorage.getItem('useStreaming');
    return stored ? JSON.parse(stored) : false;
  });

  // Default text-to-speech to ON for better accessibility
  const [useTextToSpeech, setUseTextToSpeech] = useState(() => {
    const stored = localStorage.getItem('useTextToSpeech');
    return stored ? JSON.parse(stored) : true;
  });

  useEffect(() => {
    localStorage.setItem('useStreaming', JSON.stringify(useStreaming));
    console.log(`Streaming mode toggled: ${useStreaming}`);
  }, [useStreaming]);

  useEffect(() => {
    localStorage.setItem('useTextToSpeech', JSON.stringify(useTextToSpeech));
    console.log(`Text to Speech toggled: ${useTextToSpeech}`);
  }, [useTextToSpeech]);

  return (
    <AppContext.Provider value={{
      useStreaming,
      setUseStreaming,
      useTextToSpeech,
      setUseTextToSpeech
    }}>
      {children}
    </AppContext.Provider>
  );
};
