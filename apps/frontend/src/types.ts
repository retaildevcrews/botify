export interface InputMessage {
  role: string;
  content: string;
}

export interface Message {
  inputMessage: InputMessage;
  voiceSummary?: string; // Optional field for text-to-speech
  timestamp: string;
}

export interface Input {
  messages: InputMessage[];
}
