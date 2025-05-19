export interface InputMessage {
  role: string;
  content: string;
}

export interface Message {
  inputMessage: InputMessage;
  voiceSummary?: string; // Optional field for text-to-speech
  timestamp: string;
}

export interface StreamingResponse {
  displayResponse?: string;
  voiceSummary?: string;
  [key: string]: unknown;
}

export interface Input {
  messages: InputMessage[];
}
