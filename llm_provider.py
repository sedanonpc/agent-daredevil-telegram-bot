#!/usr/bin/env python3
"""
LLM Provider Abstraction Layer
==============================
This module provides a unified interface for different LLM providers:
- OpenAI (GPT models)
- Google AI (Gemini models)  
- Vertex AI (Gemini models via OpenAI-compatible API)

Allows easy switching between providers via configuration.

Author: Agent Daredevil
"""

import os
import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, AsyncGenerator
from abc import ABC, abstractmethod
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Generate a response from the LLM."""
        pass
    
    @abstractmethod
    async def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response from the LLM."""
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Get the current model name."""
        pass
    
    def limit_response_length(self, text: str) -> str:
        """Limit response to 3-5 sentences based on content type."""
        # Split text into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
        
        # Remove empty sentences
        sentences = [s for s in sentences if s.strip()]
        
        # Check if this is a data-driven response (contains numbers, statistics, etc.)
        is_data_driven = any(re.search(r'\d+[%]?|\$\d+|\d+\.\d+', s) for s in sentences)
        
        # Determine max sentences based on content type
        max_sentences = 6 if is_data_driven else 5
        min_sentences = 3
        
        # If we have fewer sentences than the minimum, return all of them
        if len(sentences) <= min_sentences:
            return text
        
        # If we have more sentences than the maximum, truncate
        if len(sentences) > max_sentences:
            # Always include the last sentence if it contains data summary
            if is_data_driven and any(re.search(r'\d+[%]?|\$\d+|\d+\.\d+', sentences[-1])):
                return ' '.join(sentences[:max_sentences-1] + [sentences[-1]])
            else:
                return ' '.join(sentences[:max_sentences])
        
        # Otherwise return all sentences
        return text

class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4"):
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"OpenAI provider initialized with model: {model}")
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Generate response using OpenAI API."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            response = self.client.chat.completions.create(**kwargs)
            raw_response = response.choices[0].message.content.strip()
            
            # Apply response length limit
            return self.limit_response_length(raw_response)
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    async def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using OpenAI API."""
        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": True
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            stream = self.client.chat.completions.create(**kwargs)
            
            # For streaming, we'll collect the entire response and then limit it
            full_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Apply response length limit on the fly
                    limited_response = self.limit_response_length(full_response)
                    
                    # If the limited response is shorter than what we've accumulated,
                    # we've hit our sentence limit
                    if len(limited_response) < len(full_response):
                        # Stop streaming
                        break
                    
                    yield content
                    
        except Exception as e:
            logger.error(f"OpenAI streaming error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model

class GeminiProvider(LLMProvider):
    """Google AI Gemini provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash-exp"):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self.genai = genai
        self.model_name = model
        
        # Simple model initialization - no custom safety settings
        self.model = genai.GenerativeModel(model)
        logger.info(f"Gemini provider initialized with model: {model}")
    
    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Convert OpenAI format messages to Gemini format."""
        gemini_messages = []
        system_content = None
        
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            # Convert OpenAI roles to Gemini roles
            if role == "system":
                # Store system content to prepend to next user message
                system_content = content
            elif role == "user":
                # Combine system content with user message if available
                if system_content:
                    combined_content = f"System: {system_content}\n\nUser: {content}"
                    system_content = None  # Reset after using
                else:
                    combined_content = content
                
                gemini_messages.append({
                    "role": "user", 
                    "parts": [combined_content]
                })
            elif role == "assistant":
                gemini_messages.append({
                    "role": "model",
                    "parts": [content]
                })
        
        return gemini_messages
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Generate response using Gemini API."""
        try:
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages(messages)
            
            # Configure generation
            generation_config = {}
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            if temperature is not None:
                generation_config["temperature"] = temperature
            
            # For single-turn generation, use generate_content with just the last message
            if len(gemini_messages) == 1:
                response = self.model.generate_content(
                    gemini_messages[0]["parts"][0],
                    generation_config=generation_config if generation_config else None
                )
                
                # Check if response was blocked by safety filters
                if response.candidates and response.candidates[0].finish_reason == 2:
                    logger.warning("Gemini response blocked by safety filters")
                    return "I understand your question, but I'm unable to provide a response due to content safety guidelines. Could you please rephrase your question?"
                
                # Check if response has text content
                if not response.text:
                    logger.warning("Gemini response has no text content")
                    return "I'm having trouble generating a response right now. Please try rephrasing your question."
                
                raw_response = response.text.strip()
            else:
                # For multi-turn, create a chat and send messages
                chat = self.model.start_chat()
                
                # Send all but the last message to build context
                for msg in gemini_messages[:-1]:
                    if msg["role"] == "user":
                        chat.send_message(msg["parts"][0])
                
                # Send the final message and get response
                response = chat.send_message(
                    gemini_messages[-1]["parts"][0],
                    generation_config=generation_config if generation_config else None
                )
                
                # Check if response was blocked by safety filters
                if response.candidates and response.candidates[0].finish_reason == 2:
                    logger.warning("Gemini response blocked by safety filters")
                    return "I understand your question, but I'm unable to provide a response due to content safety guidelines. Could you please rephrase your question?"
                
                # Check if response has text content
                if not response.text:
                    logger.warning("Gemini response has no text content")
                    return "I'm having trouble generating a response right now. Please try rephrasing your question."
                
                raw_response = response.text.strip()
            
            # Apply response length limit
            return self.limit_response_length(raw_response)
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "I encountered an error processing your request. Please try again."
    
    async def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using Gemini API."""
        try:
            # Add instruction to keep responses concise (3-5 sentences)
            system_msg = {"role": "system", "content": "Keep your responses concise, using only 3-5 sentences. Only use up to 6 sentences for data-heavy responses, with the last sentence including a data summary."}
            
            # Check if there's already a system message
            has_system = any(msg["role"] == "system" for msg in messages)
            
            # If there's a system message, modify it; otherwise add our own
            if has_system:
                for i, msg in enumerate(messages):
                    if msg["role"] == "system":
                        messages[i]["content"] = msg["content"] + "\n\n" + system_msg["content"]
                        break
            else:
                messages = [system_msg] + messages
                
            # Convert messages to Gemini format
            gemini_messages = self._convert_messages(messages)
            
            # Configure generation
            generation_config = {}
            if max_tokens:
                generation_config["max_output_tokens"] = max_tokens
            if temperature is not None:
                generation_config["temperature"] = temperature
            
            # For streaming, we'll collect the entire response and then limit it
            full_response = ""
            
            # For streaming, use generate_content with stream=True
            if len(gemini_messages) == 1:
                response = self.model.generate_content(
                    gemini_messages[0]["parts"][0],
                    generation_config=generation_config if generation_config else None,
                    stream=True
                )
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        content = chunk.text
                        full_response += content
                        
                        # Apply response length limit on the fly
                        limited_response = self.limit_response_length(full_response)
                        
                        # If the limited response is shorter than what we've accumulated,
                        # we've hit our sentence limit
                        if len(limited_response) < len(full_response):
                            # Stop streaming
                            break
                        
                        yield content
            else:
                # For multi-turn streaming
                chat = self.model.start_chat()
                
                # Build context with previous messages
                for msg in gemini_messages[:-1]:
                    if msg["role"] == "user":
                        chat.send_message(msg["parts"][0])
                
                # Stream the final response
                response = chat.send_message(
                    gemini_messages[-1]["parts"][0],
                    generation_config=generation_config if generation_config else None,
                    stream=True
                )
                
                for chunk in response:
                    if hasattr(chunk, 'text') and chunk.text:
                        content = chunk.text
                        full_response += content
                        
                        # Apply response length limit on the fly
                        limited_response = self.limit_response_length(full_response)
                        
                        # If the limited response is shorter than what we've accumulated,
                        # we've hit our sentence limit
                        if len(limited_response) < len(full_response):
                            # Stop streaming
                            break
                        
                        yield content
                        
        except Exception as e:
            logger.error(f"Gemini streaming error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model_name

class VertexAIProvider(LLMProvider):
    """Vertex AI Gemini provider using OpenAI-compatible API."""
    
    def __init__(self, project_id: str, location: str = "us-central1", model: str = "google/gemini-2.0-flash-001"):
        from google.auth import default
        import google.auth.transport.requests
        import openai
        
        # Get Google Cloud credentials
        credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        credentials.refresh(google.auth.transport.requests.Request())
        
        # Initialize OpenAI client with Vertex AI endpoint
        self.client = openai.OpenAI(
            base_url=f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/locations/{location}/endpoints/openapi",
            api_key=credentials.token,
        )
        
        self.model = model
        self.project_id = project_id
        self.location = location
        logger.info(f"Vertex AI provider initialized with model: {model}")
    
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        stream: bool = False
    ) -> str:
        """Generate response using Vertex AI API."""
        try:
            # Add instruction to keep responses concise (3-5 sentences)
            system_msg = {"role": "system", "content": "Keep your responses concise, using only 3-5 sentences. Only use up to 6 sentences for data-heavy responses, with the last sentence including a data summary."}
            
            # Check if there's already a system message
            has_system = any(msg["role"] == "system" for msg in messages)
            
            # If there's a system message, modify it; otherwise add our own
            if has_system:
                for i, msg in enumerate(messages):
                    if msg["role"] == "system":
                        messages[i]["content"] = msg["content"] + "\n\n" + system_msg["content"]
                        break
            else:
                messages = [system_msg] + messages
                
            kwargs = {
                "model": self.model,
                "messages": messages
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            response = self.client.chat.completions.create(**kwargs)
            raw_response = response.choices[0].message.content.strip()
            
            # Apply response length limit
            return self.limit_response_length(raw_response)
            
        except Exception as e:
            logger.error(f"Vertex AI API error: {e}")
            raise
    
    async def generate_stream(
        self, 
        messages: List[Dict[str, str]], 
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> AsyncGenerator[str, None]:
        """Generate streaming response using Vertex AI API."""
        try:
            # Add instruction to keep responses concise (3-5 sentences)
            system_msg = {"role": "system", "content": "Keep your responses concise, using only 3-5 sentences. Only use up to 6 sentences for data-heavy responses, with the last sentence including a data summary."}
            
            # Check if there's already a system message
            has_system = any(msg["role"] == "system" for msg in messages)
            
            # If there's a system message, modify it; otherwise add our own
            if has_system:
                for i, msg in enumerate(messages):
                    if msg["role"] == "system":
                        messages[i]["content"] = msg["content"] + "\n\n" + system_msg["content"]
                        break
            else:
                messages = [system_msg] + messages
                
            kwargs = {
                "model": self.model,
                "messages": messages,
                "stream": True
            }
            
            if max_tokens:
                kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                kwargs["temperature"] = temperature
            
            stream = self.client.chat.completions.create(**kwargs)
            
            # For streaming, we'll collect the entire response and then limit it
            full_response = ""
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    
                    # Apply response length limit on the fly
                    limited_response = self.limit_response_length(full_response)
                    
                    # If the limited response is shorter than what we've accumulated,
                    # we've hit our sentence limit
                    if len(limited_response) < len(full_response):
                        # Stop streaming
                        break
                    
                    yield content
                    
        except Exception as e:
            logger.error(f"Vertex AI streaming error: {e}")
            raise
    
    def get_model_name(self) -> str:
        return self.model

class LLMProviderFactory:
    """Factory class to create LLM providers based on configuration."""
    
    @staticmethod
    def create_provider(provider_type: str = None) -> LLMProvider:
        """Create and return an LLM provider based on configuration."""
        
        if provider_type is None:
            provider_type = os.getenv('LLM_PROVIDER', 'openai').lower()
        
        if provider_type == 'openai':
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")
            
            model = os.getenv('OPENAI_MODEL', 'gpt-4')
            return OpenAIProvider(api_key, model)
        
        elif provider_type == 'gemini':
            api_key = os.getenv('GOOGLE_AI_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_AI_API_KEY environment variable is required for Gemini provider")
            
            model = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash-exp')
            return GeminiProvider(api_key, model)
        
        elif provider_type == 'vertex_ai':
            project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
            if not project_id:
                raise ValueError("GOOGLE_CLOUD_PROJECT_ID environment variable is required for Vertex AI provider")
            
            location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
            model = os.getenv('VERTEX_AI_MODEL', 'google/gemini-2.0-flash-001')
            return VertexAIProvider(project_id, location, model)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider_type}")

# Convenience function to get the configured provider
def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    return LLMProviderFactory.create_provider()

# Example usage
if __name__ == "__main__":
    async def test_providers():
        """Test different LLM providers."""
        test_messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello! Tell me a short joke."}
        ]
        
        providers_to_test = ['openai', 'gemini', 'vertex_ai']
        
        for provider_name in providers_to_test:
            try:
                print(f"\n=== Testing {provider_name.upper()} Provider ===")
                provider = LLMProviderFactory.create_provider(provider_name)
                
                response = await provider.generate_response(
                    test_messages, 
                    max_tokens=100, 
                    temperature=0.7
                )
                
                print(f"Model: {provider.get_model_name()}")
                print(f"Response: {response}")
                
            except Exception as e:
                print(f"Failed to test {provider_name}: {e}")
    
    # Run the test
    asyncio.run(test_providers()) 