import axios, { AxiosError } from 'axios';
import { v4 as uuidv4 } from 'uuid';

// Type definitions
export interface Message {
  role: 'human' | 'ai' | 'user';
  content: string;
}

export interface SearchDocument {
  page_content?: {
    title?: string;
    location?: string;
    chunk?: string;
  };
}

export interface SingleQuestionResponse {
  answer: string;
  search_documents?: SearchDocument[];
}

// Define a type for the chat response
export interface ChatResponse {
  message: string;
  // Add other properties that your API returns
}

// API configuration
// Get the API URL from window.env (for runtime) or from the proxy
const API_URL = (typeof window !== 'undefined' && (window as any).env?.VITE_API_URL) ?? '/api';

// Helper functions
export const getOrCreateIds = (): { sessionId: string; userId: string } => {
  let sessionId = localStorage.getItem('sessionId');
  let userId = localStorage.getItem('userId');

  if (!sessionId) {
    sessionId = uuidv4();
    localStorage.setItem('sessionId', sessionId);
  }

  if (!userId) {
    userId = uuidv4();
    localStorage.setItem('userId', userId);
  }

  return { sessionId, userId };
};

export const sendChatMessage = async (
  message: string,
  sessionId: string,
  userId: string
): Promise<ChatResponse> => {
  if (!message || !sessionId || !userId) {
    throw new Error('Missing required parameters: message, sessionId, or userId');
  }

  try {
    const response = await axios.post(`${API_URL}/invoke`, {
      input: {
        messages: [
          {
            role: 'user',
            content: message
          }
        ]
      },
      config: {
        configurable: {
          session_id: sessionId,
          user_id: userId
        }
      }
    });
    return response.data;
  } catch (error) {
    const errorMessage = error instanceof AxiosError 
      ? `Error ${error.response?.status ?? ''}: ${error.message}` 
      : 'An unknown error occurred';
    console.error('Error sending chat message:', errorMessage);
    throw new Error('Failed to send message. Please try again.');
  }
};

export const processSingleQuestion = async (
  question: string,
  sessionId: string,
  userId: string
): Promise<SingleQuestionResponse> => {
  if (!question || !sessionId || !userId) {
    throw new Error('Missing required parameters: question, sessionId, or userId');
  }

  try {
    const response = await axios.post(`${API_URL}/question`, {
      query: question,
      session_id: sessionId,
      user_id: userId
    });
    return response.data;
  } catch (error) {
    const errorMessage = error instanceof AxiosError 
      ? `Error ${error.response?.status ?? ''}: ${error.message}` 
      : 'An unknown error occurred';
    console.error('Error processing single question:', errorMessage);
    throw new Error('Failed to process question. Please try again.');
  }
};

// Function to parse search document chunks
export const parseSearchDocumentChunk = (chunk: string): { summary: string; content: string } => {
  if (!chunk) {
    return { summary: '', content: '' };
  }

  const lines = chunk.split("\n");
  let summary = '';
  let content = '';
  
  // Find lines that contain summary and content (based on Streamlit implementation)
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (trimmedLine.startsWith("Summary:")) {
      summary = trimmedLine.substring(8).trim();
    } else if (trimmedLine.startsWith("Content:")) {
      content = trimmedLine.substring(8).trim();
    }
  }
  
  return { summary, content };
};