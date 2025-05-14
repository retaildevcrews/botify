import { useState, useRef } from 'react';
import { InputMessage, Message } from '../types';

export function useMessageManager() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  const [isStreamComplete, setIsStreamComplete] = useState(false);
  const botMessageCreatedRef = useRef(false);

  const addUserMessage = (content: string) => {
    const inputMessage: InputMessage = {
      role: 'user',
      content: content
    };

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
