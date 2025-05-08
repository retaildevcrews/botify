import { useState, useRef } from 'react';
import { flushSync } from 'react-dom';
import './App.css';
import ChatContainer from './components/ChatContainer/ChatContainer';
import SettingsDrawer from './components/SettingsDrawer/SettingsDrawer';
import { processUserInput } from './services/messageService';
import { useMessageManager } from './hooks/useMessageManager';
import { AppProvider, useAppContext } from './context/AppContext';

const AppContent = () => {
  // const [messages, setMessages] = useState<Message[]>([]);
  // const [input, setInput] = useState('');
  // const [useStreaming, setUseStreaming] = useState(() => {
  //   const stored = localStorage.getItem('useStreaming');
  //   return stored ? JSON.parse(stored) : false;
  // });
  // const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  // // Use this ref to track if we've created a bot message for streaming
  // const botMessageCreatedRef = useRef(false);

  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const { useStreaming } = useAppContext();

  // Use the custom hook for message management
  const messageManager = useMessageManager();
  const {
    messages,
    isWaitingForBotResponse,
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot
  } = messageManager;

  const sendMessage = () => {
    if (!input.trim()) return;

    const currentInput = input;

    // Note: The InputContainer component now handles clearing the textarea
    // when Enter is pressed, but we still need to clear it here for the Send button
    setInput(''); // Clear input for when the send button is clicked

    // Make the API call non-blocking for better responsiveness
    processUserInput(
      currentInput,
      useStreaming,
      messageManager
    ).catch(error => {
      console.error('Error processing message:', error);
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();

      // Get the current input value directly from the event target for immediacy
      const currentInput = (e.target as HTMLTextAreaElement).value.trim();

      // Only proceed if there's actual input
      if (!currentInput) return;

      // Clear input field immediately
      flushSync(() => {
        setInput('');
      });

      // Process the message with the captured value
      processUserInput(
        currentInput,
        useStreaming,
        messageManager
      ).catch(error => {
        console.error('Error processing message:', error);
      });
    }
  };

  // Process speech result using the shared message processing function
  const processSpeechResult = async (transcriptText: string) => {
    if (!transcriptText.trim()) return;

    await processUserInput(
      transcriptText,
      useStreaming,
      messageManager
    );
  };

  const handleMicrophoneClick = async () => {
    try {
      const speechService = await import('./services/speechService');

      if (isListening) {
        console.log('Stopping speech recognition...');
        const partialTranscript = await speechService.stopSpeechRecognition();
        setIsListening(false);

        if (partialTranscript?.trim()) {
          await processSpeechResult(partialTranscript.trim());
        }
        return;
      }

      setIsListening(true);
      console.log('Starting speech recognition...');

      const transcript = await speechService.startSpeechRecognition();

      if (transcript?.trim()) {
        await processSpeechResult(transcript.trim());
      }
    } catch (error) {
      console.error('Speech recognition failed:', error);
    } finally {
      setIsListening(false);
    }
  };

  return (
    <div className="root-container">
      <div className="header">
        <div>Botify</div>
        <div className="toggle-container">
          <SettingsDrawer />
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
        isListening={isListening}
      />
    </div>
  );
};

  // const sendMessage = async () => {
  //   console.log('sendMessage called with input:', input);
  //   if (!input.trim()) {
  //     console.log('Input is empty, message not sent');
  //     return;
  //   }

  //   const inputMessage: InputMessage = {
  //     role: 'user',
  //     content: input
  //   };

  //   const userMessage: Message = {
  //     inputMessage: inputMessage,
  //     timestamp: new Date().toISOString()
  //   };
  //   setMessages((prev) => [...prev, userMessage]);
  //   setInput('');

  //   setIsWaitingForBotResponse(true);
  //   botMessageCreatedRef.current = false;

  //   try {
  //     console.log('Sending message to API:', input);
  //     const sessionId = "session-id-placeholder";
  //     const userId = "user-id-placeholder";

  //     // Extract all previous inputMessages to create conversation history
  //     const conversationHistory: InputMessage[] = messages.map(message => message.inputMessage);
  //     // Add the current user message to the history
  //     const allMessages: InputMessage[] = [...conversationHistory, inputMessage];

  //     if (!useStreaming) {
  //       const response = await sendMessageToBot(allMessages, useStreaming, sessionId, userId);
  //       if (response) {
  //         response.timestamp = new Date().toISOString();
  //         setMessages((prev) => [...prev, response]);
  //       }
  //       setIsWaitingForBotResponse(false);
  //     } else {
  //       let lastBotMsgIndex: number | null = null;
  //       await sendMessageToBot(
  //         allMessages,
  //         useStreaming,
  //         sessionId,
  //         userId,
  //         (chunk: string) => {
  //           setIsWaitingForBotResponse(false); // streaming displayResponse done
  //           setMessages((prev) => {
  //             const updatedMessages = [...prev];
  //             // Always append to the last message, which should be our bot message
  //             if (lastBotMsgIndex === null || updatedMessages[lastBotMsgIndex]?.inputMessage.role !== 'ai') {
  //               // If no bot message exists, create a new one
  //               const newBotMessage: Message = {
  //                 inputMessage: {
  //                   role: 'ai',
  //                   content: chunk
  //                 },
  //                 timestamp: new Date().toISOString()
  //               };
  //               updatedMessages.push(newBotMessage);
  //               lastBotMsgIndex = updatedMessages.length - 1;
  //             } else {
  //               updatedMessages[lastBotMsgIndex] = {
  //                 ...updatedMessages[lastBotMsgIndex],
  //                 inputMessage: {
  //                   ...updatedMessages[lastBotMsgIndex].inputMessage,
  //                   content: updatedMessages[lastBotMsgIndex].inputMessage.content + chunk
  //                 }
  //               };
  //             }
  //             return updatedMessages;
  //           });
  //         }
  //       );
  //     }
  //   } catch (error) {
  //     console.error('Error sending message:', error);
  //   } finally {
  //     botMessageCreatedRef.current = false;
  //   }
  // };

  // const handleStreamToggle = useCallback(() => {
  //   console.log(`Streaming mode toggled: ${useStreaming}`);
  // }, [useStreaming]);

  // useEffect(() => {
  //   handleStreamToggle();
  // }, [handleStreamToggle]);

  // useEffect(() => {
  //   localStorage.setItem('useStreaming', JSON.stringify(useStreaming));
  // }, [useStreaming]);

  // const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
  //   if (e.key === 'Enter' && !e.shiftKey) {
  //     e.preventDefault();
  //     sendMessage();
  //   }
  // };

//   const handleMicrophoneClick = () => {
//     console.log('Microphone button clicked');
//   };

//   return (
//     <div className="root-container">
//       <div className="header">
//         <div>Botify</div>
//         <div className="toggle-container">
//           <SettingsDrawer
//             useStreaming={useStreaming}
//             setUseStreaming={setUseStreaming}
//           />
//         </div>
//       </div>
//       <ChatContainer
//         messages={messages}
//         input={input}
//         setInput={setInput}
//         handleKeyPress={handleKeyPress}
//         sendMessage={sendMessage}
//         handleMicrophoneClick={handleMicrophoneClick}
//         isWaitingForBotResponse={isWaitingForBotResponse}
//       />
//     </div>
//   );
// };

const App = () => {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
};

export default App;
