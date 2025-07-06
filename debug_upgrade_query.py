#!/usr/bin/env python3

import sys
sys.path.append('.')
import re

try:
    from telegram_bot_rag import _detect_statistical_query, _assess_rag_sufficiency
    
    # Test the problematic query
    test_query = "what specifics on their engineering upgrades can you share"
    
    print('🐛 Debugging "Engineering Upgrades" Query')
    print('=' * 50)
    print(f'Query: "{test_query}"')
    
    # Test statistical detection
    is_statistical = _detect_statistical_query(test_query)
    print(f'Statistical Query Detected: {is_statistical}')
    
    # Test with no RAG context (should trigger web search)
    assessment = _assess_rag_sufficiency(test_query, [])
    print(f'Empty RAG Assessment: {assessment}')
    
    # Test career vs season detection
    query_lower = test_query.lower()
    
    # Career indicators
    career_indicators = [
        r'specific\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'exact\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'precise\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'detailed\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'specifics\s+on',  # This should match!
        r'details\s+about',
        r'information\s+about'
    ]
    
    # Check each pattern
    print('\n🔍 Pattern Matching Analysis:')
    for i, pattern in enumerate(career_indicators):
        match = re.search(pattern, query_lower)
        if match:
            print(f'  ✅ Pattern {i+1}: "{pattern}" -> Match: "{match.group()}"')
        else:
            print(f'  ❌ Pattern {i+1}: "{pattern}" -> No match')
    
    # Test the actual patterns from the code
    stat_patterns = [
        r'specific\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'exact\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'precise\s+(date|data|statistics|stats|numbers|figures|info|information)',
        r'detailed\s+(date|data|statistics|stats|numbers|figures|info|information)',
    ]
    
    print('\n🧪 Current Statistical Patterns:')
    for i, pattern in enumerate(stat_patterns):
        match = re.search(pattern, query_lower)
        if match:
            print(f'  ✅ Stat Pattern {i+1}: "{pattern}" -> Match: "{match.group()}"')
        else:
            print(f'  ❌ Stat Pattern {i+1}: "{pattern}" -> No match')
    
    # Check if "specifics on" is covered
    specifics_match = re.search(r'specifics?\s+on', query_lower)
    print(f'\n🎯 "Specifics on" detection: {specifics_match.group() if specifics_match else "NOT FOUND"}')
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc() 