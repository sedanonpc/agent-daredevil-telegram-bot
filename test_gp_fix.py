#!/usr/bin/env python3
"""Test script to verify the Grand Prix ambiguity detection fix"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot_rag import _detect_query_ambiguity

def test_gp_ambiguity():
    """Test that Grand Prix queries without years are detected as ambiguous"""
    
    # Test queries that SHOULD be ambiguous (missing year)
    ambiguous_queries = [
        "who won british gp",
        "who won the british grand prix",
        "british gp winner",
        "who won at british",
        "silverstone pole position",
        "who finished first monaco grand prix",
        "italian gp results",
        "who won at monza",
        "spa winner",
        "monaco gp champion"
    ]
    
    # Test queries that should NOT be ambiguous (specific year)
    specific_queries = [
        "who won british gp 2025",
        "british grand prix 2024 winner",
        "Max Verstappen british gp 2025",
        "Lewis Hamilton silverstone 2025",
        "monaco grand prix 2025 results"
    ]
    
    print("🔍 Testing Grand Prix Ambiguity Detection Fix")
    print("=" * 60)
    
    print("\n✅ Testing AMBIGUOUS queries (should be detected):")
    for query in ambiguous_queries:
        result = _detect_query_ambiguity(query)
        status = "✅ DETECTED" if result['is_ambiguous'] else "❌ MISSED"
        print(f"  {status}: '{query}' (score: {result['ambiguity_score']:.2f})")
    
    print("\n✅ Testing SPECIFIC queries (should NOT be ambiguous):")
    for query in specific_queries:
        result = _detect_query_ambiguity(query)
        status = "✅ CORRECT" if not result['is_ambiguous'] else "❌ FALSE POSITIVE"
        print(f"  {status}: '{query}' (score: {result['ambiguity_score']:.2f})")
    
    print("\n🎯 CRITICAL TEST: The original problem query")
    test_query = "who won british gp"
    result = _detect_query_ambiguity(test_query)
    if result['is_ambiguous']:
        print(f"✅ SUCCESS: '{test_query}' is now detected as ambiguous!")
        print(f"   - Ambiguity score: {result['ambiguity_score']:.2f}")
        print(f"   - Ambiguity types: {result['ambiguity_types']}")
        print(f"   - Ambiguous phrases: {result['ambiguous_phrases']}")
    else:
        print(f"❌ FAILED: '{test_query}' is still not detected as ambiguous")
        print(f"   - This means the fix didn't work correctly")
        
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_gp_ambiguity() 