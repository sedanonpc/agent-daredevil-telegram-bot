#!/usr/bin/env python3
"""
Comprehensive LLM Provider Test Script
=====================================
Tests all configured LLM providers and their response length limitations.

Usage:
    python test_all_providers.py [--provider openai|gemini|vertex_ai] [--simple] [--gemini25]
"""

import os
import re
import asyncio
import argparse
from dotenv import load_dotenv
from llm_provider import LLMProviderFactory, get_llm_provider

# ANSI colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_colored(text, color):
    """Print colored text to terminal."""
    print(f"{color}{text}{Colors.ENDC}")

def count_sentences(text):
    """Count the number of sentences in text using regex."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return len([s for s in sentences if s.strip()])

def is_data_driven(text):
    """Check if text contains data-driven content."""
    return bool(re.search(r'\d+[%]?|\$\d+|\d+\.\d+', text))

async def run_simple_test():
    """Run a simple test of the current provider (equivalent to test_simple.py)."""
    print_colored("🔍 Simple Provider Test", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    try:
        provider = get_llm_provider()
        print_colored(f"Using provider: {provider.get_model_name()}", Colors.BLUE)
        
        response = await provider.generate_response(
            messages=[{"role": "user", "content": "Tell me about the history of basketball"}],
            temperature=0.7
        )
        
        sentence_count = count_sentences(response)
        print_colored(f"Response has {sentence_count} sentences.", Colors.GREEN)
        print_colored("\nResponse:", Colors.GREEN)
        print_colored(response, Colors.ENDC)
        
        return True
    except Exception as e:
        print_colored(f"❌ Error: {e}", Colors.RED)
        return False

async def test_gemini25():
    """Test specifically the Gemini 2.5 Flash model."""
    print_colored("🤖 Gemini 2.5 Flash Model Test", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    # Save original environment settings
    original_provider = os.getenv('LLM_PROVIDER')
    original_model = os.getenv('GEMINI_MODEL')
    
    try:
        # Temporarily set environment to use Gemini 2.5 Flash
        os.environ['LLM_PROVIDER'] = 'gemini'
        os.environ['GEMINI_MODEL'] = 'gemini-2.5-flash'
        
        print_colored("\n📋 Testing Configuration:", Colors.BLUE)
        print_colored(f"Provider: gemini", Colors.CYAN)
        print_colored(f"Model: gemini-2.5-flash", Colors.CYAN)
        
        # Create Gemini provider
        try:
            provider = LLMProviderFactory.create_provider('gemini')
            print_colored(f"✅ Provider initialized: {provider.get_model_name()}", Colors.GREEN)
            
            # Test with a simple prompt
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Keep responses concise."},
                {"role": "user", "content": "What are the key features of Gemini 2.5 Flash? Respond in 3 bullet points."}
            ]
            
            print_colored("\n📝 Generating response...", Colors.BLUE)
            
            # Generate response
            response = await provider.generate_response(
                messages=messages,
                max_tokens=200,
                temperature=0.7
            )
            
            print_colored("\n💬 Response:", Colors.GREEN)
            print_colored(response, Colors.ENDC)
            
            # Test streaming
            print_colored("\n🌊 Testing streaming response...", Colors.BLUE)
            print_colored("Question: What makes you different from other AI models?", Colors.CYAN)
            
            stream_messages = [
                {"role": "system", "content": "You are a helpful assistant. Be concise."},
                {"role": "user", "content": "What makes you different from other AI models? Answer in 2-3 sentences."}
            ]
            
            print_colored("\n🔄 Streaming response:", Colors.YELLOW)
            try:
                async for chunk in provider.generate_stream(stream_messages, max_tokens=150, temperature=0.7):
                    print(chunk, end='', flush=True)
                print("\n")  # Add newline after streaming
            except Exception as e:
                print_colored(f"\nStreaming error: {e}", Colors.RED)
            
            return True
            
        except Exception as e:
            print_colored(f"❌ Error: {e}", Colors.RED)
            print_colored("Make sure you have a valid Google AI API key set in your .env file.", Colors.YELLOW)
            print_colored("Get an API key from: https://makersuite.google.com/app/apikey", Colors.YELLOW)
            return False
            
    finally:
        # Restore original environment settings
        if original_provider:
            os.environ['LLM_PROVIDER'] = original_provider
        if original_model:
            os.environ['GEMINI_MODEL'] = original_model
        
        print_colored("\n✅ Test completed. Environment settings restored.", Colors.GREEN)

async def test_provider(provider_name):
    """Test a specific LLM provider."""
    print_colored(f"\n{'=' * 50}", Colors.HEADER)
    print_colored(f"Testing {provider_name.upper()} Provider", Colors.HEADER)
    print_colored(f"{'=' * 50}", Colors.HEADER)
    
    try:
        # Create provider
        provider = LLMProviderFactory.create_provider(provider_name)
        print_colored(f"✅ Provider initialized: {provider.get_model_name()}", Colors.GREEN)
        
        # Test cases
        test_cases = [
            {
                "name": "Small Talk",
                "messages": [
                    {"role": "user", "content": "Hello, how are you today?"}
                ],
                "max_sentences": 3
            },
            {
                "name": "General Knowledge",
                "messages": [
                    {"role": "user", "content": "Tell me about the planet Mars."}
                ],
                "max_sentences": 5
            },
            {
                "name": "Technical Explanation",
                "messages": [
                    {"role": "user", "content": "Explain how quantum computing works."}
                ],
                "max_sentences": 5
            },
            {
                "name": "Data-Heavy Question",
                "messages": [
                    {"role": "user", "content": "What are the statistics on global smartphone usage in 2023?"}
                ],
                "max_sentences": 6
            }
        ]
        
        # Run tests
        for test in test_cases:
            print_colored(f"\n📝 Testing: {test['name']}", Colors.CYAN)
            print_colored(f"Query: {test['messages'][0]['content']}", Colors.BLUE)
            
            try:
                # Generate response
                response = await provider.generate_response(
                    messages=test["messages"],
                    temperature=0.7
                )
                
                # Count sentences
                sentence_count = count_sentences(response)
                data_driven = is_data_driven(response)
                
                print_colored(f"\n💬 Response ({sentence_count} sentences):", Colors.GREEN)
                print_colored(response, Colors.ENDC)
                
                # Check if within limits
                max_allowed = test["max_sentences"]
                if data_driven and max_allowed < 6:
                    max_allowed = 6  # Allow up to 6 for data-driven responses
                
                if 3 <= sentence_count <= max_allowed:
                    print_colored(f"✅ PASS: Response has {sentence_count} sentences (target: 3-{max_allowed})", Colors.GREEN)
                    print_colored(f"Data-driven: {'Yes' if data_driven else 'No'}", Colors.BLUE)
                else:
                    print_colored(f"❌ FAIL: Response has {sentence_count} sentences (outside target range of 3-{max_allowed})", Colors.RED)
                    
            except Exception as e:
                print_colored(f"❌ Error: {e}", Colors.RED)
        
        return True
            
    except Exception as e:
        print_colored(f"❌ Failed to initialize {provider_name} provider: {e}", Colors.RED)
        return False

async def main():
    """Run the comprehensive test suite."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Test LLM providers')
    parser.add_argument('--provider', choices=['openai', 'gemini', 'vertex_ai'], 
                        help='Specific provider to test (tests all if not specified)')
    parser.add_argument('--simple', action='store_true',
                        help='Run a simple test of the current provider')
    parser.add_argument('--gemini25', action='store_true',
                        help='Test specifically the Gemini 2.5 Flash model')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Run simple test if requested
    if args.simple:
        await run_simple_test()
        return
        
    # Run Gemini 2.5 test if requested
    if args.gemini25:
        await test_gemini25()
        return
    
    print_colored("🔍 LLM Provider Comprehensive Test", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    # Determine which providers to test
    providers_to_test = []
    if args.provider:
        providers_to_test = [args.provider]
    else:
        # Test all available providers
        providers_to_test = ['openai', 'gemini', 'vertex_ai']
        
        # Filter out providers without required environment variables
        if not os.getenv('OPENAI_API_KEY'):
            providers_to_test.remove('openai')
        if not os.getenv('GOOGLE_AI_API_KEY'):
            providers_to_test.remove('gemini')
        if not os.getenv('GOOGLE_CLOUD_PROJECT_ID'):
            providers_to_test.remove('vertex_ai')
    
    # Run tests
    results = {}
    for provider in providers_to_test:
        results[provider] = await test_provider(provider)
    
    # Summary
    print_colored("\n\n📊 Test Results Summary", Colors.HEADER)
    print_colored("=" * 50, Colors.HEADER)
    
    for provider, success in results.items():
        status = f"{Colors.GREEN}✅ PASS" if success else f"{Colors.RED}❌ FAIL"
        print(f"{status}: {provider.upper()}{Colors.ENDC}")
    
    print_colored("\n✅ Test completed.", Colors.GREEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print_colored("\n🛑 Test interrupted by user", Colors.YELLOW)
    except Exception as e:
        print_colored(f"❌ Unexpected error: {e}", Colors.RED) 