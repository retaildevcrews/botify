import { useState, useRef } from 'react';
import { InputMessage, Message } from '../types';

// Export the return type of useMessageManager for use in other files
export type MessageManager = ReturnType<typeof useMessageManager>;

export function useMessageManager() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  const [isStreamComplete, setIsStreamComplete] = useState(false);
  const botMessageCreatedRef = useRef(false);

  // Add a new overloaded version of addUserMessage that accepts both string and InputMessage
  const addUserMessage = (contentOrMessage: string | InputMessage) => {
    let inputMessage: InputMessage;

    // Check if the input is a string or an InputMessage
    if (typeof contentOrMessage === 'string') {
      inputMessage = {
        role: 'user',
        content: contentOrMessage
      };
    } else {
      inputMessage = contentOrMessage;
    }

    const userMessage: Message = {
      inputMessage: inputMessage,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);

    // Extract all previous inputMessages to create conversation history
    const conversationHistory: InputMessage[] = messages.map(message => message.inputMessage);
    // Add the current user message to the history and return result
    return [...conversationHistory, inputMessage];
  };

  const addBotMessage = (botMessage: Message) => {
    setMessages(prev => [...prev, botMessage]);
  };

  const updateOrAddBotMessage = (content: string) => {
    if (!content) {
      return;
    }

    setMessages(prev => {
      const updatedMessages = [...prev];
      const lastBotIndex = updatedMessages.findIndex(
        (msg, i) => msg.inputMessage.role === 'ai' && i === updatedMessages.length - 1
      );

      if (lastBotIndex === -1) {
        // Add new bot message
        return [...updatedMessages, {
          inputMessage: {
            role: 'ai',
            content: content
          },
          timestamp: new Date().toISOString()
        }];
      } else {
        // Update existing bot message
        const updatedMsg = {
          ...updatedMessages[lastBotIndex],
          inputMessage: {
            ...updatedMessages[lastBotIndex].inputMessage,
            content: updatedMessages[lastBotIndex].inputMessage.content + content
          }
        };
        return [
          ...updatedMessages.slice(0, lastBotIndex),
          updatedMsg,
          ...updatedMessages.slice(lastBotIndex + 1)
        ];
      }
    });
  };

  const resetWaitingStates = () => {
    setIsWaitingForBotResponse(false);
  };

  const setWaitingForBot = () => {
    setIsWaitingForBotResponse(true);
    botMessageCreatedRef.current = false;
  };

  const setStreamComplete = (value: boolean = false) => {
    setIsStreamComplete(value);
  };

  return {
    messages,
    isWaitingForBotResponse,
    botMessageCreatedRef,
    addUserMessage,
    addBotMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot,
    isStreamComplete,
    setStreamComplete
  };
}
