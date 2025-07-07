#!/usr/bin/env python3
"""
Test the ambiguity detection system to ensure it correctly identifies and handles
ambiguous queries that were previously causing hallucination.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from telegram_bot_rag import _detect_query_ambiguity, _create_clarifying_questions, _detect_sport_domain

def test_temporal_ambiguity():
    """Test detection of temporal ambiguity patterns"""
    print("=== Testing Temporal Ambiguity Detection ===")
    
    temporal_queries = [
        "who won the race earlier?",
        "what happened in the game last night?",
        "british grand prix 2025 results",  # This should NOT be ambiguous
        "who's starting on pole this weekend?",
        "the championship this year",
        "recent performance",
        "earlier today",
        "that season",
        "the latest race",
        "who won yesterday?"
    ]
    
    for query in temporal_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Types: {result['ambiguity_types']}")
        print(f"  Phrases: {result['ambiguous_phrases']}")
        print()

def test_event_ambiguity():
    """Test detection of event ambiguity patterns"""
    print("=== Testing Event Ambiguity Detection ===")
    
    event_queries = [
        "when is the next race?",
        "who is competing in the championship?",
        "what time is the event?",
        "the qualifying results",
        "pole position this weekend",
        "the finals",
        "upcoming match",
        "Max Verstappen pole position Silverstone 2025",  # This should NOT be ambiguous
        "schedule for the tournament"
    ]
    
    for query in event_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Types: {result['ambiguity_types']}")
        print(f"  Phrases: {result['ambiguous_phrases']}")
        print()

def test_pronoun_ambiguity():
    """Test detection of pronoun ambiguity patterns"""
    print("=== Testing Pronoun Ambiguity Detection ===")
    
    pronoun_queries = [
        "he won the race",
        "his performance was great",
        "they are competing today",
        "her stats this season",
        "Lewis Hamilton won the race",  # This should NOT be ambiguous
        "them in the playoffs",
        "she scored 30 points",
        "his championship chances"
    ]
    
    for query in pronoun_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Types: {result['ambiguity_types']}")
        print(f"  Phrases: {result['ambiguous_phrases']}")
        print()

def test_possessive_ambiguity():
    """Test detection of possessive ambiguity patterns"""
    print("=== Testing Possessive Ambiguity Detection ===")
    
    possessive_queries = [
        "my favorite driver's stats",
        "your team's performance",
        "that guy's pole positions",
        "the player's recent games",
        "our team in the playoffs",
        "Lewis Hamilton's career wins",  # This should NOT be ambiguous
        "their championship hopes",
        "this person's achievements"
    ]
    
    for query in possessive_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Types: {result['ambiguity_types']}")
        print(f"  Phrases: {result['ambiguous_phrases']}")
        print()

def test_clarification_questions():
    """Test the clarification question generation for different sports"""
    print("=== Testing Clarification Question Generation ===")
    
    test_cases = [
        {
            'query': "who won the race earlier?",
            'sport': 'f1',
            'expected_types': ['temporal']
        },
        {
            'query': "the game last night",
            'sport': 'nba',
            'expected_types': ['temporal']
        },
        {
            'query': "he finished on pole",
            'sport': 'f1',
            'expected_types': ['pronoun']
        },
        {
            'query': "their championship chances",
            'sport': 'general',
            'expected_types': ['possessive']
        }
    ]
    
    for test_case in test_cases:
        query = test_case['query']
        ambiguity_data = _detect_query_ambiguity(query)
        
        print(f"Query: '{query}'")
        print(f"Detected Sport: {_detect_sport_domain(query)}")
        print(f"Expected Types: {test_case['expected_types']}")
        print(f"Detected Types: {ambiguity_data['ambiguity_types']}")
        
        if ambiguity_data['is_ambiguous']:
            clarification = _create_clarifying_questions(query, ambiguity_data)
            print(f"Clarification Questions:")
            print(clarification)
        else:
            print("No clarification needed")
        
        print("-" * 50)

def test_non_ambiguous_queries():
    """Test that clear, specific queries are NOT marked as ambiguous"""
    print("=== Testing Non-Ambiguous Queries ===")
    
    clear_queries = [
        "Lewis Hamilton's career race wins total",
        "Max Verstappen pole positions in 2025",
        "British Grand Prix 2025 race results",
        "LeBron James points in 2024-25 season",
        "Lakers vs Warriors January 15 2025",
        "Current F1 championship standings",
        "NBA standings Eastern Conference",
        "Fernando Alonso podium finishes career",
        "Stephen Curry three-pointers this season",
        "Mercedes AMG F1 team wins 2025"
    ]
    
    for query in clear_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']} (should be False)")
        print(f"  Confidence: {result['confidence']:.2f} (should be low)")
        
        if result['is_ambiguous']:
            print(f"  ❌ INCORRECTLY MARKED AS AMBIGUOUS!")
            print(f"  Types: {result['ambiguity_types']}")
            print(f"  Phrases: {result['ambiguous_phrases']}")
        else:
            print(f"  ✅ Correctly identified as non-ambiguous")
        print()

def test_mixed_ambiguity():
    """Test queries with mixed ambiguity levels"""
    print("=== Testing Mixed Ambiguity Levels ===")
    
    mixed_queries = [
        "british grand prix earlier",  # Partially ambiguous
        "Max Verstappen's performance recently",  # Partially ambiguous
        "the race results for Hamilton",  # Partially ambiguous
        "LeBron James in that game",  # Partially ambiguous
        "current championship standings",  # Possibly ambiguous
        "latest F1 news"  # Possibly ambiguous
    ]
    
    for query in mixed_queries:
        result = _detect_query_ambiguity(query)
        print(f"Query: '{query}'")
        print(f"  Ambiguous: {result['is_ambiguous']}")
        print(f"  Confidence: {result['confidence']:.2f}")
        print(f"  Types: {result['ambiguity_types']}")
        print(f"  Phrases: {result['ambiguous_phrases']}")
        
        if result['is_ambiguous']:
            print(f"  Should trigger clarification: {result['confidence'] > 0.4}")
        print()

def main():
    """Run all ambiguity detection tests"""
    print("🔍 AMBIGUITY DETECTION SYSTEM TEST SUITE")
    print("=" * 60)
    
    test_temporal_ambiguity()
    test_event_ambiguity()
    test_pronoun_ambiguity()
    test_possessive_ambiguity()
    test_clarification_questions()
    test_non_ambiguous_queries()
    test_mixed_ambiguity()
    
    print("✅ All tests completed!")
    print("\n📊 SUMMARY:")
    print("- The ambiguity detection system should catch vague queries")
    print("- Specific queries with names/dates should NOT be marked ambiguous")
    print("- Clarification questions should be sport-specific")
    print("- High confidence ambiguity (>0.7) should trigger immediate clarification")
    print("- Moderate ambiguity (>0.4) should trigger clarification if results are poor")

if __name__ == "__main__":
    main() 