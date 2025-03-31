import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, getOrCreateIds, sendChatMessage } from '../helpers/api';
import { HumanIcon, BotIcon } from '../components/icons';
import styles from './InputField.module.css';

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { sessionId, userId } = getOrCreateIds();

  // Initialize with welcome message
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        { 
          role: 'ai', 
          content: 'Hello, I am a bot using FastAPI Streaming. How can I help you?' 
        }
      ]);
    }
  }, [messages.length]);

  // Scroll to bottom of messages
  const scrollToBottom = (): void => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage: Message = { role: 'human', content: input.trim() };
    const currentInput = input.trim(); // Store the current input value
    
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      // Send message to API
      const response = await sendChatMessage(currentInput, sessionId, userId);
      
      // Add AI response to chat
      if (response) {
        // Extract the message content from the ChatResponse object
        const responseContent = typeof response === 'string' 
          ? response 
          : response.message || JSON.stringify(response, null, 2);
          
        const aiMessage: Message = { 
          role: 'ai', 
          content: responseContent 
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error('Empty response received from the server');
      }
    } catch (err: unknown) {
      setError('Failed to get a response from the AI. Please try again.');
      console.error('Error in chat:', err instanceof Error ? err.message : String(err));
    } finally {
      setIsLoading(false);
    }
  };

  // Generate unique IDs for messages to avoid using array index as key
  const getMessageKey = (message: Message, index: number): string => {
    return `message-${message.role}-${index}-${message.content.substring(0, 10).replace(/\s+/g, '-')}`;
  };

  return (
    <div className="page-container">
      <h2 className="page-title">Chat with Botify</h2>
      <div className="chat-container">
        <div className="chat-messages" aria-live="polite">
          {messages.map((message, index) => (
            <div 
              key={getMessageKey(message, index)} 
              className={`message ${message.role === 'human' ? 'human-message' : 'ai-message'}`}
              aria-label={`${message.role === 'human' ? 'You' : 'Bot'}: ${message.content.substring(0, 20)}...`}
            >
              <div className="message-icon" aria-hidden="true">
                {message.role === 'human' ? <HumanIcon size={28} /> : <BotIcon size={28} />}
              </div>
              <div className="message-content">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="spinner" aria-label="Loading response"></div>
          )}
          {error && (
            <div className="error-message" role="alert">{error}</div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={handleSubmit} className={styles.inputContainer}>
          <label htmlFor="chat-input" className="sr-only">Type your message</label>
          <input
            id="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message here..."
            className={styles.inputField}
            disabled={isLoading}
            aria-required="true"
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={isLoading || !input.trim()}
            aria-label="Send message"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;