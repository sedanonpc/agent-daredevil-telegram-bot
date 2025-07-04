#!/usr/bin/env python3
"""
Session Memory System for Agent Daredevil
========================================

Provides persistent conversation memory that survives bot restarts.
Stores conversation history in SQLite database with user isolation.
"""

import sqlite3
import json
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from pathlib import Path
import os

@dataclass
class Message:
    """Represents a single message in conversation history"""
    id: Optional[int] = None
    user_id: int = 0
    role: str = "user"  # "user" or "assistant"
    content: str = ""
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None

@dataclass
class ConversationSession:
    """Represents a conversation session for a user"""
    session_id: str
    user_id: int
    created_at: datetime
    last_activity: datetime
    message_count: int = 0
    is_active: bool = True

class SessionMemoryManager:
    """Manages conversation sessions and message history"""
    
    def __init__(self, db_path: str = "./memory.db", max_session_messages: int = 50, 
                 session_timeout_hours: int = 24):
        self.db_path = db_path
        self.max_session_messages = max_session_messages
        self.session_timeout_hours = session_timeout_hours
        self.lock = threading.Lock()
        
        # Ensure database directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        
        # Clean up old sessions periodically
        self._cleanup_old_sessions()
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS conversation_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_activity TIMESTAMP NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1
                )
            ''')
            
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES conversation_sessions (session_id)
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_session 
                ON messages (session_id, timestamp)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_messages_user 
                ON messages (user_id, timestamp)
            ''')
            
            conn.commit()
    
    def get_or_create_session(self, user_id: int) -> ConversationSession:
        """Get active session for user or create new one"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Check for active session
                cursor = conn.execute('''
                    SELECT session_id, user_id, created_at, last_activity, message_count
                    FROM conversation_sessions
                    WHERE user_id = ? AND is_active = 1
                    ORDER BY last_activity DESC
                    LIMIT 1
                ''', (user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    session_id, user_id, created_at, last_activity, message_count = row
                    
                    # Check if session is still valid
                    last_activity_dt = datetime.fromisoformat(last_activity)
                    timeout_threshold = datetime.now() - timedelta(hours=self.session_timeout_hours)
                    
                    if last_activity_dt > timeout_threshold:
                        # Update last activity
                        conn.execute('''
                            UPDATE conversation_sessions 
                            SET last_activity = ?
                            WHERE session_id = ?
                        ''', (datetime.now().isoformat(), session_id))
                        conn.commit()
                        
                        return ConversationSession(
                            session_id=session_id,
                            user_id=user_id,
                            created_at=datetime.fromisoformat(created_at),
                            last_activity=datetime.now(),
                            message_count=message_count,
                            is_active=True
                        )
                
                # Create new session
                session_id = f"session_{user_id}_{int(time.time())}"
                now = datetime.now()
                
                conn.execute('''
                    INSERT INTO conversation_sessions 
                    (session_id, user_id, created_at, last_activity, message_count, is_active)
                    VALUES (?, ?, ?, ?, 0, 1)
                ''', (session_id, user_id, now.isoformat(), now.isoformat()))
                
                conn.commit()
                
                return ConversationSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=now,
                    last_activity=now,
                    message_count=0,
                    is_active=True
                )
    
    def add_message(self, user_id: int, role: str, content: str) -> bool:
        """Add a message to the conversation history"""
        if not content.strip():
            return False
        
        session = self.get_or_create_session(user_id)
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Add message
                conn.execute('''
                    INSERT INTO messages (session_id, user_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (session.session_id, user_id, role, content, datetime.now().isoformat()))
                
                # Update session message count and last activity
                conn.execute('''
                    UPDATE conversation_sessions 
                    SET message_count = message_count + 1,
                        last_activity = ?
                    WHERE session_id = ?
                ''', (datetime.now().isoformat(), session.session_id))
                
                conn.commit()
                
                # Check if we need to limit messages
                self._limit_session_messages(session.session_id)
                
                return True
    
    def get_conversation_history(self, user_id: int, limit: int = 10) -> List[Message]:
        """Get recent conversation history for a user"""
        session = self.get_or_create_session(user_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT id, user_id, role, content, timestamp, session_id
                FROM messages
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            ''', (session.session_id, limit))
            
            messages = []
            for row in cursor.fetchall():
                messages.append(Message(
                    id=row[0],
                    user_id=row[1],
                    role=row[2],
                    content=row[3],
                    timestamp=datetime.fromisoformat(row[4]),
                    session_id=row[5]
                ))
            
            return list(reversed(messages))  # Return in chronological order
    
    def get_context_for_llm(self, user_id: int, max_messages: int = 10) -> str:
        """Get formatted conversation context for LLM"""
        messages = self.get_conversation_history(user_id, max_messages)
        
        if not messages:
            return ""
        
        context_parts = ["RECENT CONVERSATION:"]
        
        # Add recent messages
        recent_messages = messages[-10:]  # Last 10 messages
        for message in recent_messages:
            role_label = "USER" if message.role == "user" else "ASSISTANT"
            context_parts.append(f"{role_label}: {message.content}")
        
        return "\n".join(context_parts)
    
    def clear_user_history(self, user_id: int) -> bool:
        """Clear all conversation history for a user"""
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Mark sessions as inactive
                conn.execute('''
                    UPDATE conversation_sessions 
                    SET is_active = 0
                    WHERE user_id = ?
                ''', (user_id,))
                
                # Delete messages
                conn.execute('''
                    DELETE FROM messages 
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
    
    def _limit_session_messages(self, session_id: str):
        """Limit the number of messages in a session"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT COUNT(*) FROM messages WHERE session_id = ?
            ''', (session_id,))
            
            message_count = cursor.fetchone()[0]
            
            if message_count > self.max_session_messages:
                # Delete oldest messages, keeping the most recent ones
                conn.execute('''
                    DELETE FROM messages 
                    WHERE session_id = ? 
                    AND id NOT IN (
                        SELECT id FROM messages 
                        WHERE session_id = ?
                        ORDER BY timestamp DESC 
                        LIMIT ?
                    )
                ''', (session_id, session_id, self.max_session_messages))
                
                conn.commit()
    
    def _cleanup_old_sessions(self):
        """Clean up old inactive sessions"""
        cutoff_time = datetime.now() - timedelta(days=7)  # Keep sessions for 7 days
        
        with self.lock:
            with sqlite3.connect(self.db_path) as conn:
                # Delete old messages
                conn.execute('''
                    DELETE FROM messages 
                    WHERE session_id IN (
                        SELECT session_id FROM conversation_sessions 
                        WHERE last_activity < ?
                    )
                ''', (cutoff_time.isoformat(),))
                
                # Delete old sessions
                conn.execute('''
                    DELETE FROM conversation_sessions 
                    WHERE last_activity < ?
                ''', (cutoff_time.isoformat(),))
                
                conn.commit()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                SELECT 
                    COUNT(DISTINCT session_id) as active_sessions,
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT user_id) as unique_users
                FROM messages
                WHERE session_id IN (
                    SELECT session_id FROM conversation_sessions WHERE is_active = 1
                )
            ''')
            
            stats = cursor.fetchone()
            
            return {
                "active_sessions": stats[0] if stats else 0,
                "total_messages": stats[1] if stats else 0,
                "unique_users": stats[2] if stats else 0,
                "database_path": self.db_path,
                "max_session_messages": self.max_session_messages,
                "session_timeout_hours": self.session_timeout_hours
            }

# Global instance
_memory_manager = None

def get_memory_manager(db_path: str = "./memory.db", max_session_messages: int = 50, 
                      session_timeout_hours: int = 24) -> SessionMemoryManager:
    """Get or create global memory manager instance"""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = SessionMemoryManager(db_path, max_session_messages, session_timeout_hours)
    return _memory_manager

if __name__ == "__main__":
    # Test the memory system
    print("Testing Session Memory System...")
    
    manager = get_memory_manager()
    
    # Test user interaction
    test_user_id = 12345
    
    print(f"Adding test messages for user {test_user_id}...")
    manager.add_message(test_user_id, "user", "Hello, my name is John")
    manager.add_message(test_user_id, "assistant", "Hi John! Nice to meet you.")
    manager.add_message(test_user_id, "user", "What's my name?")
    
    print("Getting conversation history...")
    history = manager.get_conversation_history(test_user_id)
    
    for msg in history:
        print(f"  {msg.role}: {msg.content}")
    
    print("\nGetting LLM context...")
    context = manager.get_context_for_llm(test_user_id)
    print(context)
    
    print("\nMemory system statistics:")
    stats = manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    print("\nSession memory system test completed!") 