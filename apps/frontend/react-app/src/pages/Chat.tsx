import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { Message, getOrCreateIds, sendChatMessage } from '../helpers/api';
import { HumanIcon, BotIcon } from '../components/icons';

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
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    // Add user message to chat
    const userMessage: Message = { role: 'human', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    try {
      // Send message to API
      const response = await sendChatMessage(input, sessionId, userId);
      
      // Add AI response to chat
      const aiMessage: Message = { role: 'ai', content: response.toString() };
      setMessages(prev => [...prev, aiMessage]);
    } catch (err) {
      setError('Failed to get a response from the AI. Please try again.');
      console.error('Error in chat:', err);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="page-container">
      <h2 className="page-title">Chat with Botify</h2>
      <div className="chat-container">
        <div className="chat-messages">
          {messages.map((message, index) => (
            <div 
              key={index} 
              className={`message ${message.role === 'human' ? 'human-message' : 'ai-message'}`}
            >
              <div className="message-icon">
                {message.role === 'human' ? <HumanIcon size={28} /> : <BotIcon size={28} />}
              </div>
              <div className="message-content">
                <ReactMarkdown>{message.content}</ReactMarkdown>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="spinner"></div>
          )}
          {error && (
            <div className="error-message">{error}</div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <form onSubmit={handleSubmit} className="input-container">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message here..."
            className="input-field"
            disabled={isLoading}
          />
          <button 
            type="submit" 
            className="send-button"
            disabled={isLoading || !input.trim()}
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
};

export default Chat;