import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';

// Type definitions
export interface Message {
  role: 'human' | 'ai';
  content: string;
}

export interface SearchDocument {
  page_content: {
    title: string;
    location: string;
    chunk: string;
  };
}

export interface SingleQuestionResponse {
  answer: string;
  search_documents: SearchDocument[];
}

// API configuration
// Get the API URL from window.env (for runtime) or from the proxy
const API_URL = (window as any).env?.VITE_API_URL || '/api';

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
): Promise<Response> => {
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
    console.error('Error sending chat message:', error);
    throw error;
  }
};

export const processSingleQuestion = async (
  question: string,
  sessionId: string,
  userId: string
): Promise<SingleQuestionResponse> => {
  try {
    const response = await axios.post(`${API_URL}/question`, {
      query: question,
      session_id: sessionId,
      user_id: userId
    });
    return response.data;
  } catch (error) {
    console.error('Error processing single question:', error);
    throw error;
  }
};

// Function to parse search document chunks
export const parseSearchDocumentChunk = (chunk: string): { summary: string; content: string } => {
  const lines = chunk.split("\n");
  let summary = '';
  let content = '';
  
  // Find lines that contain summary and content (based on Streamlit implementation)
  for (const line of lines) {
    if (line.trim().startsWith("Summary:")) {
      summary = line.trim().substring(8);
    } else if (line.trim().startsWith("Content:")) {
      content = line.trim().substring(8);
    }
  }
  
  return { summary, content };
};