#!/usr/bin/env python3
"""
Botify Chat CLI - A simple command line tool to test Botify's chat endpoints

This script allows you to interact with both the regular and streaming endpoints
of the Botify bot service. It supports conversation history and provides a nice
display of streaming responses.

Usage:
  python test_chat_cli.py
  
Options:
  --stream       Use streaming mode (default)
  --no-stream    Use regular invoke endpoint
  --url URL      Specify custom bot service URL (default: http://localhost:8080)
  --help         Show this help message

Author: Botify Team
"""

import argparse
import json
import os
import sys
import time
from typing import List, Dict, Any, Optional
import uuid
import requests
import sseclient

# ANSI color codes for prettier output
GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
END = "\033[0m"


class BotifyChat:
    def __init__(self, base_url: str = "http://localhost:8080", streaming: bool = True):
        """Initialize the Botify chat client"""
        self.base_url = base_url
        self.streaming = streaming
        self.session_id = str(uuid.uuid4())
        self.user_id = "cli-test-user"
        self.conversation_history: List[Dict[str, str]] = []

        # Immediately check connection and available endpoints
        self._check_connection()

    def _check_connection(self):
        """Check connection to server and display available endpoints"""
        try:
            # Try to access root endpoint to see what's available
            response = requests.get(f"{self.base_url}")
            print(f"{BLUE}Connected to server: {self.base_url}{END}")
            
            # Try to access docs endpoint to see available APIs
            try:
                docs_response = requests.get(f"{self.base_url}/docs")
                if docs_response.status_code == 200:
                    print(f"{GREEN}API docs available at: {self.base_url}/docs{END}")
            except:
                pass
                
        except requests.RequestException as e:
            print(f"{RED}Warning: Could not connect to server: {e}{END}")
            print(f"{YELLOW}Proceeding anyway, but requests may fail...{END}")

    def send_message(self, message: str) -> None:
        """Send a message to the Botify service"""
        if not message.strip():
            print(f"{YELLOW}Empty message. Please type something.{END}")
            return

        # Add the user message to conversation history
        self.conversation_history.append({"role": "user", "content": message})
        
        # Prepare the request payload
        payload = {
            "input": {
                "messages": self.conversation_history
            },
            "config": {
                "configurable": {
                    "session_id": self.session_id,
                    "user_id": self.user_id
                }
            }
        }
        
        print(f"\n{BLUE}User: {END}{message}\n")
        print(f"{GREEN}Assistant: {END}", end="", flush=True)
        
        if self.streaming:
            self._stream_response(payload)
        else:
            self._invoke_response(payload)
            
    def _invoke_response(self, payload: Dict[str, Any]) -> None:
        """Get a response using the regular invoke endpoint"""
        try:
            print(f"{YELLOW}DEBUG: Sending request to {self.base_url}/invoke{END}")
            response = requests.post(
                f"{self.base_url}/invoke",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                print(f"{RED}Error: Received status code {response.status_code}{END}")
                print(f"{RED}{response.text}{END}")
                return
                
            data = response.json()
            if "messages" in data:
                assistant_message = data["messages"][-1]["content"]
            else:
                # Handle structured response formats
                assistant_message = json.dumps(data, indent=2)
                
            print(assistant_message)
            
            # Add to conversation history
            self.conversation_history.append({"role": "assistant", "content": assistant_message})
            
        except requests.RequestException as e:
            print(f"{RED}Error connecting to Botify service: {e}{END}")
        except json.JSONDecodeError:
            print(f"{RED}Error parsing response as JSON{END}")
            
    def _stream_response(self, payload: Dict[str, Any]) -> None:
        """Get a streaming response using the invoke/stream endpoint"""
        try:
            print(f"{YELLOW}DEBUG: Sending request to {self.base_url}/invoke/stream{END}")
            response = requests.post(
                f"{self.base_url}/invoke/stream",
                json=payload,
                headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
                stream=True
            )
            
            if response.status_code != 200:
                print(f"{RED}Error: Received status code {response.status_code}{END}")
                print(f"{RED}{response.text}{END}")
                
                # Try non-streaming as fallback
                if response.status_code == 404:
                    print(f"{YELLOW}Streaming endpoint not found. Trying regular endpoint...{END}")
                    self._invoke_response(payload)
                return
            
            print(f"{GREEN}Got streaming response, reading...{END}")
            
            # Manual SSE parsing as a fallback if sseclient has issues
            try:
                client = sseclient.SSEClient(response)
                full_response = ""
                
                for event in client.events():
                    print(f"{YELLOW}DEBUG: Received event: {event.data[:30]}...{END}")
                    
                    if event.data == "[DONE]":
                        print(f"{YELLOW}DEBUG: Received DONE signal{END}")
                        break
                        
                    try:
                        data = json.loads(event.data)
                        if "content" in data:
                            chunk = data["content"]
                            print(chunk, end="", flush=True)
                            full_response += chunk
                        elif "error" in data:
                            print(f"{RED}{data['error']}{END}")
                    except json.JSONDecodeError:
                        print(f"{RED}Error parsing event data: {event.data}{END}")
                        
            except Exception as e:
                # Fallback manual parsing if SSEClient fails
                print(f"{YELLOW}SSEClient failed, using manual parsing: {e}{END}")
                buffer = ''
                full_response = ""
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        line = line.strip()
                        if line.startswith('data: '):
                            data = line[6:]  # Strip "data: " prefix
                            if data == "[DONE]":
                                break
                                
                            try:
                                parsed = json.loads(data)
                                if "content" in parsed:
                                    chunk = parsed["content"]
                                    print(chunk, end="", flush=True)
                                    full_response += chunk
                            except json.JSONDecodeError:
                                print(f"{RED}Error parsing data: {data}{END}")
                
            print("\n")  # Add a newline after streaming completes
            
            # Add to conversation history
            if full_response:
                self.conversation_history.append({"role": "assistant", "content": full_response})
            else:
                print(f"{RED}Warning: No content was received from streaming response{END}")
                
        except requests.RequestException as e:
            print(f"{RED}Error connecting to Botify service: {e}{END}")
        except Exception as e:
            print(f"{RED}Unexpected error in streaming: {e}{END}")

    def list_endpoints(self) -> None:
        """Try to detect available endpoints on the server"""
        try:
            print(f"{BLUE}Checking available endpoints on {self.base_url}...{END}")
            
            # Common endpoints to check
            endpoints = [
                "/", 
                "/docs", 
                "/openapi.json", 
                "/invoke", 
                "/invoke/stream",
                "/bot",
                "/chat",
                "/v1/chat/completions"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}")
                    status = f"{GREEN}Found{END}" if response.status_code < 400 else f"{RED}Not found{END}"
                    print(f"Endpoint {endpoint}: {status} (Status {response.status_code})")
                except requests.RequestException:
                    print(f"Endpoint {endpoint}: {RED}Error{END}")
            
        except Exception as e:
            print(f"{RED}Error checking endpoints: {e}{END}")
            
    def run(self):
        """Run the interactive chat loop"""
        print(f"{BOLD}{BLUE}Welcome to Botify Chat CLI!{END}")
        print(f"Session ID: {self.session_id}")
        print(f"Mode: {'Streaming' if self.streaming else 'Regular'}")
        print(f"Bot URL: {self.base_url}")
        print(f"{YELLOW}Type 'exit', 'quit', or press Ctrl+C to end the session.{END}")
        print(f"{YELLOW}Type 'endpoints' to list available endpoints.{END}\n")
        
        try:
            while True:
                user_input = input(f"{BOLD}> {END}")
                
                if user_input.lower() in ['exit', 'quit']:
                    print(f"{BLUE}Goodbye!{END}")
                    break
                
                if user_input.lower() == 'endpoints':
                    self.list_endpoints()
                    continue
                    
                self.send_message(user_input)
                
        except KeyboardInterrupt:
            print(f"\n{BLUE}Session terminated. Goodbye!{END}")


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="Botify Chat CLI")
    parser.add_argument("--stream", dest="streaming", action="store_true", help="Use streaming mode (default)")
    parser.add_argument("--no-stream", dest="streaming", action="store_false", help="Use regular invoke endpoint")
    parser.add_argument("--url", type=str, default="http://localhost:8080", help="Specify custom bot service URL")
    parser.set_defaults(streaming=True)
    
    args = parser.parse_args()
    
    # Create and run the chat client
    chat = BotifyChat(base_url=args.url, streaming=args.streaming)
    chat.run()


if __name__ == "__main__":
    main()