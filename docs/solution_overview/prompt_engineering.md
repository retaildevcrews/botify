# GenAI Chatbot: Prompt Engineering
  
This document describes how the GenAI Chatbot prompt is put together. This guide is designed to help you understand the different sections of the prompt and how they contribute to GenAI Chatbot's behavior and responses. Each section of the prompt is explained in detail to ensure you can effectively interact with GenAI Chatbot.  This is not the actual prompt but rather a document that explains what the goal of the prompt is and how it attempts to achieve that goal.  The actual prompt is maintained in source control and is updated based on requirements/needs/evaluation results. [For information on maintaining the prompt go here](prompt_maintenance.md)
  
## Prompt Sections

1. [Instructions](#instructions)  
2. [On Safety](#on-safety)  
3. [About Your Output Format](#about-your-output-format)  
4. [On Your Ability to Answer Questions Based on Fetched Documents (Sources)](#on-your-ability-to-answer-questions-based-on-fetched-documents-sources)  
5. [Examples](#examples)  
  
## Instructions  
  
- Overview

  - This section outlines the fundamental rules and behaviors that GenAI Chatbot must follow. It ensures that GenAI Chatbot remains consistent,
  polite, and focused on its primary function: answering questions from a knowledge base  
  
- Prompting Concepts

  - **Instructions**: These are explicit commands that GenAI Chatbot must follow. They dictate how GenAI Chatbot should behave in various situations.  
  - **Behavioral Guidelines**: These include rules on how to handle confrontations, stress, and the tone of responses.  
  
## On Safety  
  
- Overview

  - This section ensures that GenAI Chatbot operates within ethical boundaries and maintains user safety. It includes rules to prevent harmful or inappropriate content.  
  
- Prompting Concepts

  - **Instructions**: Specific commands to refuse certain types of requests.  
  - **Ethical Guidelines**: Rules to ensure that GenAI Chatbot does not generate harmful or inappropriate content.  
  
## About Your Output Format  
  
- Overview

  - This section specifies the format in which GenAI Chatbot should provide its responses.  
  
## On Your Ability to Answer Questions Based on Fetched Documents (Sources)  
  
- Overview

  - This section guides GenAI Chatbot on how to use extracted parts (context) from documents to provide accurate answers. It ensures that GenAI Chatbot's responses are based on the most relevant and up-to-date information.  
  
- Prompting Concepts

  - **Contextual Responses**: Using provided context to generate answers.  
  - **Recommendation Guidelines**: Instructions on how to structure answers.  
  
## Examples  
  
- Overview

  - This section provides a set of examples to illustrate how GenAI Chatbot should respond to various types of user queries. These examples serve as templates for generating consistent and accurate responses.  
  
- Prompting Concepts

  - **Few-Shot Prompting**: This technique involves providing multiple examples to guide the AI in generating similar responses. By seeing several examples, the AI can better understand the desired format and content of its responses.  
  - **ReACT Strategy**: The Reason and Act (ReACT) strategy involves the AI reasoning through the problem and then acting based on that reasoning. This helps in generating more coherent and contextually appropriate responses.  
