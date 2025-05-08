export interface InputMessage {
  role: string;
  content: string;
}

export interface Message {
  inputMessage: InputMessage;
  timestamp: string;
}

export interface Input {
  messages: InputMessage[];
}
