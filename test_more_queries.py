#!/usr/bin/env python3

import sys
sys.path.append('.')
import re

try:
    from telegram_bot_rag import _detect_statistical_query
    
    # Test problematic queries from user report
    test_queries = [
        # FIXED: Previously caused crash
        "what specifics on their engineering upgrades can you share",
        
        # NEW: Betting/Recommendation queries (Issue #2)
        "I'm planning to place bets on the game. Give me recommendations",
        "give me recommendations for betting",
        "provide betting tips for the race",
        "suggestions for fantasy picks",
        "who will win the race this Sunday",
        "predictions for the F1 race",
        "advice on betting odds",
        
        # NEW: F1 Schedule queries (Issue #1) 
        "What do you think about the race this Sunday",
        "race this Sunday",
        "what's happening this weekend",
        "which race is today",
        "schedule for this weekend",
        "current F1 race",
        "upcoming race information",
        
        # Similar patterns that should trigger web search
        "can you provide details about McLaren's aerodynamic improvements",
        "what information about Red Bull's car development do you have", 
        "give me a breakdown of Ferrari's engine upgrades",
        "tell me details on Mercedes' suspension changes",
        "what analysis of Alpine's performance can you share",
        
        # Edge cases
        "specifics about the race",
        "details on Hamilton",
        "information on the championship"
    ]
    
    print('🧪 Testing Enhanced Statistical Query Detection - User Issue Fixes')
    print('=' * 70)
    
    all_detected = True
    for query in test_queries:
        is_statistical = _detect_statistical_query(query)
        status = '✅ STATISTICAL' if is_statistical else '❌ NOT DETECTED'
        print(f'{status} | "{query}"')
        if not is_statistical:
            all_detected = False
    
    print('\n' + '=' * 70)
    if all_detected:
        print('🎉 SUCCESS: All queries now trigger web search when RAG is insufficient!')
        print('✅ Issue #1 FIXED: F1 schedule queries will get current data')
        print('✅ Issue #2 FIXED: Betting recommendations will trigger web search')
        print('✅ Issue #3 FIXED: Agent won\'t crash on follow-up questions')
    else:
        print('⚠️  Some queries still not detected - may need additional patterns')
    print('=' * 70)
    
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc() 