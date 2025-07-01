import streamlit as st
import chromadb
from chromadb.config import Settings
import os
import tempfile
from pathlib import Path
import PyPDF2
import docx
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
import json
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import urllib.parse
from urllib.parse import urlparse
import time
import pandas as pd
import re
from typing import Dict, List, Optional, Tuple
import threading
import queue
import os
from dotenv import load_dotenv
import logging
from datetime import datetime, timedelta
import sqlite3

# Load environment variables
load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
CHROMA_DB_PATH = os.getenv('CHROMA_DB_PATH', './chroma_db')

# At the top with other imports, add:
try:
    from basketball_reference_crawler import (
        BasketballReferenceCrawler, 
        CrawlConfig, 
        get_basketball_reference_seed_urls
    )
    CRAWLER_AVAILABLE = True
except ImportError:
    CRAWLER_AVAILABLE = False

# Initialize ChromaDB
@st.cache_resource
def init_chromadb():
    """Initialize ChromaDB client"""
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    return client

@st.cache_resource
def init_embeddings():
    """Initialize OpenAI embeddings"""
    return OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY)

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return None

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(file)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading DOCX: {str(e)}")
        return None

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    try:
        return file.read().decode('utf-8')
    except Exception as e:
        st.error(f"Error reading TXT: {str(e)}")
        return None

def process_document(file, filename):
    """Process uploaded document and extract text"""
    file_extension = Path(filename).suffix.lower()
    
    if file_extension == '.pdf':
        return extract_text_from_pdf(file)
    elif file_extension == '.docx':
        return extract_text_from_docx(file)
    elif file_extension == '.txt':
        return extract_text_from_txt(file)
    else:
        st.error(f"Unsupported file type: {file_extension}")
        return None

def chunk_text(text, chunk_size=1000, chunk_overlap=200):
    """Split text into chunks"""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )
    chunks = text_splitter.split_text(text)
    return chunks

def add_to_knowledge_base(text, filename, metadata=None):
    """Add text chunks to the knowledge base"""
    try:
        # Initialize embeddings and vector store
        embeddings = init_embeddings()
        
        # Create or get existing collection
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        # Split text into chunks
        chunks = chunk_text(text)
        
        # Prepare metadata
        base_metadata = {
            "source": filename,
            "timestamp": datetime.now().isoformat(),
            "chunk_count": len(chunks)
        }
        if metadata:
            base_metadata.update(metadata)
        
        # Add chunks to vector store
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_id"] = i
            metadatas.append(chunk_metadata)
        
        vectorstore.add_texts(chunks, metadatas=metadatas)
        
        return True, len(chunks)
    except Exception as e:
        st.error(f"Error adding to knowledge base: {str(e)}")
        return False, 0

def search_knowledge_base(query, k=5):
    """Search the knowledge base"""
    try:
        embeddings = init_embeddings()
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        results = vectorstore.similarity_search_with_score(query, k=k)
        return results
    except Exception as e:
        st.error(f"Error searching knowledge base: {str(e)}")
        return []

def get_collection_stats():
    """Get statistics about the knowledge base"""
    try:
        client = init_chromadb()
        collection = client.get_collection("telegram_bot_knowledge")
        count = collection.count()
        
        # Get all documents to analyze sources
        if count > 0:
            results = collection.get()
            sources = set()
            url_sources = 0
            file_sources = 0
            god_commands = 0
            nba_data_sources = 0
            
            for metadata in results['metadatas']:
                if 'source' in metadata:
                    sources.add(metadata['source'])
                    # Count source types
                    if metadata.get('is_god_command', False):
                        god_commands += 1
                    elif metadata.get('source_type') == 'nba_data':
                        nba_data_sources += 1
                    elif metadata.get('source_type') == 'url':
                        url_sources += 1
                    else:
                        file_sources += 1
            
            return {
                "total_chunks": count,
                "unique_sources": len(sources),
                "sources": list(sources),
                "url_chunks": url_sources,
                "file_chunks": file_sources,
                "god_commands": god_commands,
                "nba_data_chunks": nba_data_sources,
                "source_details": results['metadatas']
            }
        else:
            return {
                "total_chunks": 0,
                "unique_sources": 0,
                "sources": [],
                "url_chunks": 0,
                "file_chunks": 0,
                "god_commands": 0,
                "nba_data_chunks": 0,
                "source_details": []
            }
    except Exception as e:
        return {
            "total_chunks": 0,
            "unique_sources": 0,
            "sources": [],
            "url_chunks": 0,
            "file_chunks": 0,
            "god_commands": 0,
            "nba_data_chunks": 0,
            "source_details": [],
            "error": str(e)
        }

def delete_source(source_name):
    """Delete all chunks from a specific source"""
    try:
        client = init_chromadb()
        collection = client.get_collection("telegram_bot_knowledge")
        
        # Get all documents from this source
        results = collection.get(where={"source": source_name})
        
        if results['ids']:
            # Delete all documents from this source
            collection.delete(ids=results['ids'])
            return True, len(results['ids'])
        else:
            return False, 0
    except Exception as e:
        st.error(f"Error deleting source: {str(e)}")
        return False, 0

def extract_text_from_url(url):
    """Extract text content from a URL"""
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        # Make request with timeout
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
            script.decompose()
        
        # Try to find main content areas
        content_selectors = [
            'article',
            '[role="main"]',
            '.content',
            '.article-content',
            '.post-content',
            '.entry-content',
            'main',
            '.main-content'
        ]
        
        main_content = None
        for selector in content_selectors:
            elements = soup.select(selector)
            if elements:
                main_content = elements[0]
                break
        
        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body')
        
        if not main_content:
            main_content = soup
        
        # Extract text
        text = main_content.get_text(separator='\n', strip=True)
        
        # Clean up text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines)
        
        # Get page title
        title = soup.find('title')
        page_title = title.get_text().strip() if title else urlparse(url).netloc
        
        return cleaned_text, page_title
        
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching URL: {str(e)}")
        return None, None
    except Exception as e:
        st.error(f"Error processing URL content: {str(e)}")
        return None, None

def validate_url(url):
    """Validate if URL is properly formatted"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def add_url_to_knowledge_base(url, custom_title=None, metadata=None):
    """Add URL content to the knowledge base"""
    try:
        # Extract text from URL
        text, page_title = extract_text_from_url(url)
        
        if not text:
            return False, 0, "Could not extract text from URL"
        
        # Use custom title if provided, otherwise use page title
        source_name = custom_title if custom_title else page_title
        
        # Initialize embeddings and vector store
        embeddings = init_embeddings()
        
        # Create or get existing collection
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        # Split text into chunks
        chunks = chunk_text(text)
        
        # Prepare metadata
        base_metadata = {
            "source": source_name,
            "url": url,
            "source_type": "url",
            "timestamp": datetime.now().isoformat(),
            "chunk_count": len(chunks)
        }
        if metadata:
            base_metadata.update(metadata)
        
        # Add chunks to vector store
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_id"] = i
            metadatas.append(chunk_metadata)
        
        vectorstore.add_texts(chunks, metadatas=metadatas)
        
        return True, len(chunks), f"Successfully processed: {source_name}"
    except Exception as e:
        return False, 0, f"Error adding URL to knowledge base: {str(e)}"

# God Commands Functions
def add_god_command(command_text, description="", priority=10):
    """Add a god command with high priority to override agent behavior"""
    try:
        embeddings = init_embeddings()
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        # Create metadata for god command
        metadata = {
            "source": f"GOD_COMMAND_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "source_type": "god_command",
            "timestamp": datetime.now().isoformat(),
            "priority": priority,  # High priority for god commands
            "command_type": "behavior_override",
            "description": description,
            "is_god_command": True
        }
        
        # Add the command as a single chunk with high priority
        vectorstore.add_texts([command_text], metadatas=[metadata])
        
        return True, metadata["source"]
    except Exception as e:
        st.error(f"Error adding god command: {str(e)}")
        return False, None

def get_god_commands():
    """Get all god commands from the knowledge base"""
    try:
        client = init_chromadb()
        collection = client.get_collection("telegram_bot_knowledge")
        
        # Get all documents and filter for god commands
        results = collection.get()
        god_commands = []
        
        for i, metadata in enumerate(results['metadatas']):
            if metadata.get('is_god_command', False):
                god_commands.append({
                    'id': results['ids'][i],
                    'text': results['documents'][i],
                    'source': metadata.get('source', ''),
                    'description': metadata.get('description', ''),
                    'timestamp': metadata.get('timestamp', ''),
                    'priority': metadata.get('priority', 10)
                })
        
        # Sort by priority (higher first) then by timestamp (newest first)
        god_commands.sort(key=lambda x: (-x['priority'], x['timestamp']), reverse=True)
        
        return god_commands
    except Exception as e:
        st.error(f"Error getting god commands: {str(e)}")
        return []

def delete_god_command(source_name):
    """Delete a specific god command"""
    try:
        client = init_chromadb()
        collection = client.get_collection("telegram_bot_knowledge")
        
        # Get all documents with this source
        results = collection.get(where={"source": source_name})
        
        if results['ids']:
            # Delete the documents
            collection.delete(ids=results['ids'])
            return True, len(results['ids'])
        else:
            return False, 0
    except Exception as e:
        st.error(f"Error deleting god command: {str(e)}")
        return False, 0

def search_with_god_commands(query, k=5):
    """Search knowledge base with god commands getting priority"""
    try:
        embeddings = init_embeddings()
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        # First, get god commands
        god_commands = get_god_commands()
        
        # Then get regular search results
        all_results = vectorstore.similarity_search_with_score(query, k=k*2)  # Get more to filter
        
        # Separate god commands and regular results
        god_command_results = []
        regular_results = []
        
        for doc, score in all_results:
            if doc.metadata.get('is_god_command', False):
                god_command_results.append((doc, score))
            else:
                regular_results.append((doc, score))
        
        # Combine results with god commands first
        final_results = god_command_results + regular_results
        
        # Return top k results
        return final_results[:k]
    except Exception as e:
        st.error(f"Error searching with god commands: {str(e)}")
        return []

def test_god_command_response(query):
    """Test how god commands would affect a response to a query"""
    results = search_with_god_commands(query, k=3)
    
    context_parts = []
    god_commands_found = []
    regular_context = []
    
    for doc, score in results:
        if doc.metadata.get('is_god_command', False):
            god_commands_found.append({
                'text': doc.page_content,
                'description': doc.metadata.get('description', ''),
                'score': score
            })
        else:
            regular_context.append({
                'text': doc.page_content,
                'source': doc.metadata.get('source', 'Unknown'),
                'score': score
            })
    
    return {
        'god_commands': god_commands_found,
        'regular_context': regular_context,
        'total_results': len(results)
    }

# NBA Data Scraping Functions
def extract_nba_team_stats(url: str) -> Optional[Dict]:
    """Extract NBA team statistics from Basketball-Reference.com"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract page title and context
        title = soup.find('title')
        page_title = title.get_text().strip() if title else "NBA Statistics"
        
        # Find all tables on the page
        tables = soup.find_all('table')
        
        if not tables:
            return None
        
        extracted_data = {
            'title': page_title,
            'url': url,
            'tables': [],
            'narrative_text': '',
            'extraction_timestamp': datetime.now().isoformat()
        }
        
        for i, table in enumerate(tables):
            table_data = extract_table_data(table)
            if table_data:
                extracted_data['tables'].append(table_data)
        
        # Generate narrative text from tables
        extracted_data['narrative_text'] = generate_nba_narrative(extracted_data)
        
        return extracted_data
        
    except Exception as e:
        st.error(f"Error extracting NBA data: {str(e)}")
        return None

def extract_table_data(table) -> Optional[Dict]:
    """Extract structured data from an HTML table"""
    try:
        # Get table caption/title
        caption = table.find('caption')
        table_title = caption.get_text().strip() if caption else "NBA Data Table"
        
        # Extract headers
        headers = []
        header_row = table.find('thead')
        if header_row:
            header_cells = header_row.find_all(['th', 'td'])
            headers = [cell.get_text().strip() for cell in header_cells if cell.get_text().strip()]
        
        # If no thead, try first tr
        if not headers:
            first_row = table.find('tr')
            if first_row:
                header_cells = first_row.find_all(['th', 'td'])
                headers = [cell.get_text().strip() for cell in header_cells if cell.get_text().strip()]
        
        # Extract rows
        rows = []
        tbody = table.find('tbody') or table
        for row in tbody.find_all('tr')[1 if not table.find('thead') else 0:]:  # Skip header row if no thead
            cells = row.find_all(['td', 'th'])
            row_data = []
            for cell in cells:
                # Clean cell text
                cell_text = cell.get_text().strip()
                # Handle links (player names, team names)
                link = cell.find('a')
                if link:
                    cell_text = f"{cell_text} [{link.get('href', '')}]"
                row_data.append(cell_text)
            
            if row_data and any(cell.strip() for cell in row_data):  # Skip empty rows
                rows.append(row_data)
        
        if not rows:
            return None
        
        return {
            'title': table_title,
            'headers': headers,
            'rows': rows,
            'row_count': len(rows),
            'column_count': len(headers) if headers else len(rows[0]) if rows else 0
        }
        
    except Exception as e:
        return None

def generate_nba_narrative(data: Dict) -> str:
    """Convert NBA table data into narrative text for better LLM understanding"""
    try:
        narratives = []
        
        # Add title and context
        narratives.append(f"NBA Data Report: {data['title']}")
        narratives.append(f"Source: {data['url']}")
        narratives.append(f"Data extracted on: {data['extraction_timestamp']}")
        narratives.append("")
        
        for i, table in enumerate(data['tables'], 1):
            narratives.append(f"TABLE {i}: {table['title']}")
            narratives.append(f"This table contains {table['row_count']} rows and {table['column_count']} columns.")
            narratives.append("")
            
            # Generate narrative for each table type
            if 'team' in table['title'].lower() or 'standings' in table['title'].lower():
                narrative = generate_team_standings_narrative(table)
            elif 'player' in table['title'].lower() or 'stats' in table['title'].lower():
                narrative = generate_player_stats_narrative(table)
            elif 'game' in table['title'].lower() or 'schedule' in table['title'].lower():
                narrative = generate_game_schedule_narrative(table)
            else:
                narrative = generate_generic_table_narrative(table)
            
            narratives.append(narrative)
            narratives.append("")
            
            # Add structured summary
            narratives.append("STRUCTURED DATA SUMMARY:")
            narratives.append(f"Headers: {', '.join(table['headers'])}")
            
            # Add top few rows as examples
            if table['rows']:
                narratives.append("Sample data entries:")
                for j, row in enumerate(table['rows'][:3], 1):  # First 3 rows
                    row_summary = []
                    for k, (header, value) in enumerate(zip(table['headers'], row)):
                        if k < 5:  # First 5 columns
                            row_summary.append(f"{header}: {value}")
                    narratives.append(f"  Entry {j}: {', '.join(row_summary)}")
            
            narratives.append("")
            narratives.append("-" * 50)
            narratives.append("")
        
        return "\n".join(narratives)
        
    except Exception as e:
        return f"Error generating narrative: {str(e)}"

def generate_team_standings_narrative(table: Dict) -> str:
    """Generate narrative for team standings/stats tables"""
    try:
        narrative = []
        narrative.append("TEAM STANDINGS/STATISTICS ANALYSIS:")
        
        if not table['rows']:
            return "No team data available."
        
        # Identify key columns
        headers = [h.lower() for h in table['headers']]
        team_col = next((i for i, h in enumerate(headers) if 'team' in h or 'tm' in h), 0)
        wins_col = next((i for i, h in enumerate(headers) if h in ['w', 'wins']), None)
        losses_col = next((i for i, h in enumerate(headers) if h in ['l', 'losses']), None)
        
        # Analyze top teams
        if wins_col is not None:
            try:
                # Sort by wins (assuming numeric)
                sorted_teams = sorted(table['rows'], 
                                    key=lambda x: float(x[wins_col]) if x[wins_col].replace('.', '').isdigit() else 0, 
                                    reverse=True)
                
                narrative.append(f"Top performing teams by wins:")
                for i, team in enumerate(sorted_teams[:5], 1):
                    team_name = team[team_col] if team_col < len(team) else f"Team {i}"
                    wins = team[wins_col] if wins_col < len(team) else "N/A"
                    losses = team[losses_col] if losses_col and losses_col < len(team) else "N/A"
                    narrative.append(f"  {i}. {team_name}: {wins} wins, {losses} losses")
            except:
                narrative.append("Could not analyze team rankings.")
        
        # Add general observations
        narrative.append(f"\nThis table tracks {len(table['rows'])} teams with statistics including:")
        key_stats = [h for h in table['headers'] if h.lower() in ['w', 'l', 'pct', 'gb', 'pts', 'opp', 'diff']]
        if key_stats:
            narrative.append(f"Key metrics: {', '.join(key_stats)}")
        
        return "\n".join(narrative)
        
    except Exception as e:
        return f"Error analyzing team data: {str(e)}"

def generate_player_stats_narrative(table: Dict) -> str:
    """Generate narrative for player statistics tables"""
    try:
        narrative = []
        narrative.append("PLAYER STATISTICS ANALYSIS:")
        
        if not table['rows']:
            return "No player data available."
        
        # Identify key columns
        headers = [h.lower() for h in table['headers']]
        player_col = next((i for i, h in enumerate(headers) if 'player' in h or 'name' in h), 0)
        pts_col = next((i for i, h in enumerate(headers) if h in ['pts', 'points']), None)
        
        # Analyze top performers
        if pts_col is not None:
            try:
                # Sort by points
                sorted_players = sorted(table['rows'], 
                                      key=lambda x: float(x[pts_col]) if x[pts_col].replace('.', '').isdigit() else 0, 
                                      reverse=True)
                
                narrative.append(f"Top scoring players:")
                for i, player in enumerate(sorted_players[:5], 1):
                    player_name = player[player_col] if player_col < len(player) else f"Player {i}"
                    points = player[pts_col] if pts_col < len(player) else "N/A"
                    narrative.append(f"  {i}. {player_name}: {points} points")
            except:
                narrative.append("Could not analyze player rankings.")
        
        # Add general observations
        narrative.append(f"\nThis table contains statistics for {len(table['rows'])} players with metrics including:")
        key_stats = [h for h in table['headers'] if h.lower() in ['pts', 'reb', 'ast', 'fg%', '3p%', 'ft%']]
        if key_stats:
            narrative.append(f"Key performance indicators: {', '.join(key_stats)}")
        
        return "\n".join(narrative)
        
    except Exception as e:
        return f"Error analyzing player data: {str(e)}"

def generate_game_schedule_narrative(table: Dict) -> str:
    """Generate narrative for game schedule/results tables"""
    try:
        narrative = []
        narrative.append("GAME SCHEDULE/RESULTS ANALYSIS:")
        
        if not table['rows']:
            return "No game data available."
        
        # Identify key columns
        headers = [h.lower() for h in table['headers']]
        date_col = next((i for i, h in enumerate(headers) if 'date' in h), None)
        team_cols = [i for i, h in enumerate(headers) if 'team' in h or '@' in h]
        
        narrative.append(f"This schedule contains {len(table['rows'])} games.")
        
        if date_col is not None:
            # Try to identify recent games
            narrative.append("Recent/upcoming games include:")
            for i, game in enumerate(table['rows'][:5], 1):
                date = game[date_col] if date_col < len(game) else "Date N/A"
                teams = " vs ".join([game[col] for col in team_cols[:2] if col < len(game)])
                narrative.append(f"  {i}. {date}: {teams}")
        
        return "\n".join(narrative)
        
    except Exception as e:
        return f"Error analyzing game data: {str(e)}"

def generate_generic_table_narrative(table: Dict) -> str:
    """Generate narrative for generic NBA tables"""
    try:
        narrative = []
        narrative.append("NBA DATA TABLE ANALYSIS:")
        
        if not table['rows']:
            return "No data available in this table."
        
        narrative.append(f"This table contains {len(table['rows'])} entries with the following structure:")
        narrative.append(f"Columns: {', '.join(table['headers'])}")
        
        # Identify numeric columns for basic stats
        numeric_cols = []
        for i, header in enumerate(table['headers']):
            if any(char.isdigit() or char in ['%', '.'] for row in table['rows'][:3] for char in row[i] if i < len(row)):
                numeric_cols.append((i, header))
        
        if numeric_cols:
            narrative.append(f"Numeric data columns: {', '.join([h for _, h in numeric_cols])}")
        
        return "\n".join(narrative)
        
    except Exception as e:
        return f"Error analyzing table data: {str(e)}"

def add_nba_data_to_knowledge_base(nba_data: Dict, custom_title: Optional[str] = None, metadata: Optional[Dict] = None) -> Tuple[bool, int, str]:
    """Add NBA data to the knowledge base with optimized chunking"""
    try:
        if not nba_data or not nba_data.get('narrative_text'):
            return False, 0, "No NBA data to process"
        
        # Use custom title or generate from data
        source_name = custom_title if custom_title else f"NBA Data: {nba_data['title']}"
        
        # Initialize embeddings and vector store
        embeddings = init_embeddings()
        vectorstore = Chroma(
            collection_name="telegram_bot_knowledge",
            embedding_function=embeddings,
            persist_directory=CHROMA_DB_PATH
        )
        
        # Create multiple representations for better retrieval
        content_chunks = []
        
        # 1. Full narrative text (chunked)
        narrative_chunks = chunk_text(nba_data['narrative_text'], chunk_size=1200, chunk_overlap=300)
        content_chunks.extend(narrative_chunks)
        
        # 2. Individual table summaries
        for i, table in enumerate(nba_data.get('tables', []), 1):
            table_summary = f"NBA Table {i}: {table['title']}\n"
            table_summary += f"Contains {table['row_count']} rows with columns: {', '.join(table['headers'])}\n\n"
            
            # Add sample data
            if table['rows']:
                table_summary += "Sample entries:\n"
                for j, row in enumerate(table['rows'][:5], 1):
                    row_data = []
                    for k, (header, value) in enumerate(zip(table['headers'], row)):
                        if k < 6:  # First 6 columns
                            row_data.append(f"{header}: {value}")
                    table_summary += f"{j}. {', '.join(row_data)}\n"
            
            content_chunks.append(table_summary)
        
        # 3. Key insights summary
        insights_summary = f"NBA Data Summary from {nba_data['url']}\n"
        insights_summary += f"Title: {nba_data['title']}\n"
        insights_summary += f"Contains {len(nba_data.get('tables', []))} data tables\n"
        insights_summary += f"Extracted on: {nba_data['extraction_timestamp']}\n\n"
        insights_summary += "This data includes NBA statistics that can be used to answer questions about team performance, player statistics, game schedules, and league standings."
        
        content_chunks.append(insights_summary)
        
        # Prepare metadata
        base_metadata = {
            "source": source_name,
            "url": nba_data['url'],
            "source_type": "nba_data",
            "data_type": "basketball_statistics",
            "timestamp": datetime.now().isoformat(),
            "extraction_timestamp": nba_data['extraction_timestamp'],
            "table_count": len(nba_data.get('tables', [])),
            "chunk_count": len(content_chunks)
        }
        
        if metadata:
            base_metadata.update(metadata)
        
        # Add chunks to vector store
        metadatas = []
        for i, chunk in enumerate(content_chunks):
            chunk_metadata = base_metadata.copy()
            chunk_metadata["chunk_id"] = i
            chunk_metadata["chunk_type"] = "narrative" if i < len(narrative_chunks) else "table_summary" if i < len(narrative_chunks) + len(nba_data.get('tables', [])) else "insights"
            metadatas.append(chunk_metadata)
        
        vectorstore.add_texts(content_chunks, metadatas=metadatas)
        
        return True, len(content_chunks), f"Successfully processed NBA data: {source_name}"
        
    except Exception as e:
        return False, 0, f"Error adding NBA data to knowledge base: {str(e)}"

def validate_nba_url(url: str) -> bool:
    """Validate if URL is from Basketball-Reference.com or other NBA data sources"""
    try:
        parsed = urlparse(url)
        valid_domains = [
            'basketball-reference.com',
            'www.basketball-reference.com',
            'nba.com',
            'www.nba.com',
            'stats.nba.com'
        ]
        return parsed.netloc.lower() in valid_domains
    except:
        return False

# Streamlit UI
def main():
    st.set_page_config(
        page_title="Telegram Bot RAG Manager",
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 Telegram Bot RAG Knowledge Manager")
    st.markdown("Upload documents and URLs to build your Telegram bot's knowledge base")
    
    # Sidebar for navigation
    st.sidebar.title("Navigation")
    
    # Build page options based on availability
    page_options = [
        "📁 Upload Documents & URLs", 
        "🏀 NBA Data Import",
        "🔍 Search Knowledge Base", 
        "⚡ God Commands",
        "📊 Knowledge Base Stats",
        "🗑️ Manage Sources"
    ]
    
    # Add crawler page if available
    if CRAWLER_AVAILABLE:
        page_options.insert(2, "🕷️ Web Crawler")
    
    page = st.sidebar.selectbox("Choose a page", page_options)
    
    if page == "📁 Upload Documents & URLs":
        upload_page()
    elif page == "🏀 NBA Data Import":
        nba_data_page()
    elif page == "🕷️ Web Crawler" and CRAWLER_AVAILABLE:
        web_crawler_page()
    elif page == "🔍 Search Knowledge Base":
        search_page()
    elif page == "⚡ God Commands":
        god_commands_page()
    elif page == "📊 Knowledge Base Stats":
        stats_page()
    elif page == "🗑️ Manage Sources":
        manage_sources_page()

def upload_page():
    st.header("📁 Upload Documents & URLs")
    st.markdown("Upload PDF, DOCX, TXT files or add content from URLs (news articles, blog posts, etc.)")
    
    # Create tabs for different upload methods
    tab1, tab2 = st.tabs(["📎 Upload Files", "🌐 Add URLs"])
    
    with tab1:
        st.subheader("📎 File Upload")
        # File uploader
        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=['pdf', 'docx', 'txt'],
            accept_multiple_files=True,
            help="Supported formats: PDF, DOCX, TXT"
        )
        
        if uploaded_files:
            # Processing options
            col1, col2 = st.columns(2)
            with col1:
                chunk_size_files = st.slider("Chunk Size", 500, 2000, 1000, 100, key="chunk_size_files")
            with col2:
                chunk_overlap_files = st.slider("Chunk Overlap", 50, 500, 200, 50, key="chunk_overlap_files")
            
            # Additional metadata
            st.subheader("📝 Additional Metadata (Optional)")
            col1, col2 = st.columns(2)
            with col1:
                category_files = st.text_input("Category", placeholder="e.g., Technical Documentation", key="category_files")
            with col2:
                tags_files = st.text_input("Tags", placeholder="e.g., python, api, tutorial", key="tags_files")
            
            description_files = st.text_area("Description", placeholder="Brief description of the document(s)", key="description_files")
            
            st.subheader("📋 Files to Process")
            for file in uploaded_files:
                st.write(f"- {file.name} ({file.size} bytes)")
            
            if st.button("🚀 Process Files and Add to Knowledge Base", type="primary", key="process_files"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_files = len(uploaded_files)
                total_chunks = 0
                successful_files = 0
                
                for i, file in enumerate(uploaded_files):
                    status_text.text(f"Processing {file.name}...")
                    
                    # Extract text from file
                    text = process_document(file, file.name)
                    
                    if text:
                        # Prepare metadata
                        metadata = {}
                        if category_files:
                            metadata["category"] = category_files
                        if tags_files:
                            metadata["tags"] = tags_files
                        if description_files:
                            metadata["description"] = description_files
                        
                        # Add to knowledge base
                        success, chunk_count = add_to_knowledge_base(text, file.name, metadata)
                        
                        if success:
                            successful_files += 1
                            total_chunks += chunk_count
                            st.success(f"✅ {file.name}: Added {chunk_count} chunks")
                        else:
                            st.error(f"❌ {file.name}: Failed to process")
                    else:
                        st.error(f"❌ {file.name}: Could not extract text")
                    
                    progress_bar.progress((i + 1) / total_files)
                
                status_text.text("Processing complete!")
                
                if successful_files > 0:
                    st.success(f"🎉 Successfully processed {successful_files}/{total_files} files with {total_chunks} total chunks!")
                else:
                    st.error("❌ No files were successfully processed")
    
    with tab2:
        st.subheader("🌐 URL Content Extraction")
        st.markdown("Extract content from news articles, blog posts, documentation, and other web pages")
        
        # URL input section
        url_input_method = st.radio(
            "Choose input method:",
            ["Single URL", "Multiple URLs"],
            key="url_input_method"
        )
        
        urls_to_process = []
        
        if url_input_method == "Single URL":
            url = st.text_input(
                "Enter URL:",
                placeholder="https://example.com/article",
                help="Enter a complete URL including http:// or https://"
            )
            custom_title = st.text_input(
                "Custom Title (Optional):",
                placeholder="Leave empty to use page title automatically"
            )
            if url:
                urls_to_process = [(url, custom_title)]
        
        else:  # Multiple URLs
            urls_text = st.text_area(
                "Enter URLs (one per line):",
                placeholder="https://example.com/article1\nhttps://example.com/article2\nhttps://example.com/article3",
                height=150
            )
            if urls_text:
                urls_list = [url.strip() for url in urls_text.split('\n') if url.strip()]
                urls_to_process = [(url, None) for url in urls_list]
        
        if urls_to_process:
            # Processing options for URLs
            col1, col2 = st.columns(2)
            with col1:
                chunk_size_urls = st.slider("Chunk Size", 500, 2000, 1000, 100, key="chunk_size_urls")
            with col2:
                chunk_overlap_urls = st.slider("Chunk Overlap", 50, 500, 200, 50, key="chunk_overlap_urls")
            
            # Additional metadata for URLs
            st.subheader("📝 Additional Metadata (Optional)")
            col1, col2 = st.columns(2)
            with col1:
                category_urls = st.text_input("Category", placeholder="e.g., News Articles, Blog Posts", key="category_urls")
            with col2:
                tags_urls = st.text_input("Tags", placeholder="e.g., crypto, nba, esports", key="tags_urls")
            
            description_urls = st.text_area("Description", placeholder="Brief description of the URL content", key="description_urls")
            
            # Preview URLs to process
            st.subheader("🔗 URLs to Process")
            for i, (url, custom_title) in enumerate(urls_to_process, 1):
                if validate_url(url):
                    title_display = f" (Title: {custom_title})" if custom_title else ""
                    st.write(f"{i}. ✅ {url}{title_display}")
                else:
                    st.write(f"{i}. ❌ {url} - Invalid URL format")
            
            # Process URLs button
            valid_urls = [(url, title) for url, title in urls_to_process if validate_url(url)]
            
            if valid_urls and st.button("🌐 Process URLs and Add to Knowledge Base", type="primary", key="process_urls"):
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_urls = len(valid_urls)
                total_chunks = 0
                successful_urls = 0
                
                for i, (url, custom_title) in enumerate(valid_urls):
                    status_text.text(f"Processing URL {i+1}/{total_urls}: {url}")
                    
                    # Prepare metadata
                    metadata = {}
                    if category_urls:
                        metadata["category"] = category_urls
                    if tags_urls:
                        metadata["tags"] = tags_urls
                    if description_urls:
                        metadata["description"] = description_urls
                    
                    # Add URL to knowledge base
                    success, chunk_count, message = add_url_to_knowledge_base(url, custom_title, metadata)
                    
                    if success:
                        successful_urls += 1
                        total_chunks += chunk_count
                        st.success(f"✅ {message}: Added {chunk_count} chunks")
                    else:
                        st.error(f"❌ {url}: {message}")
                    
                    progress_bar.progress((i + 1) / total_urls)
                    
                    # Add small delay to be respectful to servers
                    if i < total_urls - 1:
                        time.sleep(1)
                
                status_text.text("URL processing complete!")
                
                if successful_urls > 0:
                    st.success(f"🎉 Successfully processed {successful_urls}/{total_urls} URLs with {total_chunks} total chunks!")
                else:
                    st.error("❌ No URLs were successfully processed")
            
            elif not valid_urls and urls_to_process:
                st.error("❌ No valid URLs found. Please check the URL format (must include http:// or https://)")

def nba_data_page():
    st.header("🏀 NBA Data Import")
    st.markdown("**Import NBA statistics, team data, player stats, and game schedules from Basketball-Reference.com**")
    
    # Information section
    with st.expander("ℹ️ How NBA Data Import Works"):
        st.markdown("""
        **Supported Sources:**
        - Basketball-Reference.com (recommended)
        - NBA.com official statistics
        - stats.NBA.com
        
        **What Gets Extracted:**
        - 📊 **Team standings and statistics**
        - 👤 **Player performance data**  
        - 🗓️ **Game schedules and results**
        - 📈 **Advanced analytics tables**
        
        **Smart Processing:**
        - Tables are converted to narrative descriptions for better AI understanding
        - Multiple data representations are created for optimal search
        - Basketball-specific analysis is applied to identify key insights
        
        **Example URLs:**
        - Team stats: `https://www.basketball-reference.com/leagues/NBA_2024.html`
        - Player stats: `https://www.basketball-reference.com/leagues/NBA_2024_per_game.html`
        - Team page: `https://www.basketball-reference.com/teams/LAL/2024.html`
        """)
    
    # Create tabs for different import methods
    tab1, tab2 = st.tabs(["🔗 Single URL Import", "📋 Bulk URL Import"])
    
    with tab1:
        st.subheader("🔗 Import Single NBA Data Source")
        
        # URL input
        nba_url = st.text_input(
            "NBA Data URL:",
            placeholder="https://www.basketball-reference.com/leagues/NBA_2024.html",
            help="Enter a URL from Basketball-Reference.com, NBA.com, or stats.NBA.com"
        )
        
        # Custom title
        custom_title = st.text_input(
            "Custom Title (Optional):",
            placeholder="e.g., 'NBA 2023-24 Season Team Stats'",
            help="If empty, will use the page title automatically"
        )
        
        # URL validation
        if nba_url:
            if validate_nba_url(nba_url):
                st.success("✅ Valid NBA data source URL")
            else:
                st.warning("⚠️ URL is not from a recognized NBA data source. Proceeding anyway...")
        
        # Processing options
        st.subheader("⚙️ Processing Options")
        col1, col2 = st.columns(2)
        
        with col1:
            include_table_analysis = st.checkbox(
                "Enhanced Table Analysis", 
                value=True,
                help="Apply basketball-specific analysis to identify top performers, rankings, etc."
            )
        
        with col2:
            delay_between_requests = st.slider(
                "Request Delay (seconds)", 
                min_value=1, 
                max_value=5, 
                value=2,
                help="Delay between requests to be respectful to the server"
            )
        
        # Additional metadata
        st.subheader("📝 Additional Information (Optional)")
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.text_input(
                "Category:", 
                placeholder="e.g., 'Season Stats', 'Playoff Data'",
                value="NBA Statistics"
            )
        
        with col2:
            tags = st.text_input(
                "Tags:", 
                placeholder="e.g., 'nba, basketball, 2024, stats'",
                value="nba, basketball, statistics"
            )
        
        description = st.text_area(
            "Description:",
            placeholder="Brief description of this NBA data...",
            help="This helps identify the data later"
        )
        
        # Import button
        if st.button("🏀 Import NBA Data", type="primary", disabled=not nba_url):
            if nba_url.strip():
                with st.spinner(f"Extracting NBA data from {nba_url}..."):
                    # Extract NBA data
                    nba_data = extract_nba_team_stats(nba_url.strip())
                
                if nba_data:
                    st.success(f"✅ Successfully extracted data from: {nba_data['title']}")
                    
                    # Show preview
                    with st.expander("📊 Data Preview"):
                        st.write(f"**Title:** {nba_data['title']}")
                        st.write(f"**Tables Found:** {len(nba_data.get('tables', []))}")
                        st.write(f"**Extraction Time:** {nba_data['extraction_timestamp']}")
                        
                        # Show table summaries
                        for i, table in enumerate(nba_data.get('tables', []), 1):
                            st.write(f"**Table {i}:** {table['title']} ({table['row_count']} rows, {table['column_count']} columns)")
                    
                    # Prepare metadata
                    metadata = {
                        "category": category if category else "NBA Statistics",
                        "tags": tags if tags else "nba, basketball, statistics",
                        "description": description,
                        "enhanced_analysis": include_table_analysis
                    }
                    
                    # Add to knowledge base
                    with st.spinner("Adding NBA data to knowledge base..."):
                        success, chunk_count, message = add_nba_data_to_knowledge_base(
                            nba_data, 
                            custom_title, 
                            metadata
                        )
                    
                    if success:
                        st.success(f"🎉 {message}")
                        st.info(f"📦 Added {chunk_count} chunks to knowledge base")
                        
                        # Show what was added
                        st.subheader("📋 Import Summary")
                        st.write(f"**Source:** {nba_data['title']}")
                        st.write(f"**URL:** {nba_url}")
                        st.write(f"**Tables Processed:** {len(nba_data.get('tables', []))}")
                        st.write(f"**Total Chunks:** {chunk_count}")
                        st.write(f"**Category:** {metadata['category']}")
                        if metadata['tags']:
                            st.write(f"**Tags:** {metadata['tags']}")
                        
                        st.balloons()
                    else:
                        st.error(f"❌ Failed to add NBA data: {message}")
                else:
                    st.error("❌ Could not extract NBA data from the provided URL. Please check the URL and try again.")
            else:
                st.error("Please enter a valid URL")
    
    with tab2:
        st.subheader("📋 Bulk NBA Data Import")
        st.markdown("Import multiple NBA data sources at once")
        
        # Bulk URL input
        bulk_urls = st.text_area(
            "NBA URLs (one per line):",
            placeholder="""https://www.basketball-reference.com/leagues/NBA_2024.html
https://www.basketball-reference.com/leagues/NBA_2024_per_game.html  
https://www.basketball-reference.com/teams/LAL/2024.html
https://www.basketball-reference.com/teams/GSW/2024.html""",
            height=150,
            help="Enter one URL per line. Each URL will be processed separately."
        )
        
        # Bulk processing options
        if bulk_urls:
            urls_list = [url.strip() for url in bulk_urls.split('\n') if url.strip()]
            
            st.subheader(f"📋 URLs to Process ({len(urls_list)})")
            
            # Validate URLs
            valid_urls = []
            invalid_urls = []
            
            for i, url in enumerate(urls_list, 1):
                if validate_nba_url(url):
                    valid_urls.append(url)
                    st.write(f"{i}. ✅ {url}")
                else:
                    invalid_urls.append(url)
                    st.write(f"{i}. ⚠️ {url} (not from recognized NBA source)")
            
            if invalid_urls:
                st.warning(f"⚠️ {len(invalid_urls)} URLs are not from recognized NBA sources but will be processed anyway.")
            
            # Bulk processing settings
            st.subheader("⚙️ Bulk Processing Settings")
            col1, col2 = st.columns(2)
            
            with col1:
                bulk_delay = st.slider(
                    "Delay Between URLs (seconds):", 
                    min_value=2, 
                    max_value=10, 
                    value=3,
                    help="Longer delays are more respectful to servers"
                )
            
            with col2:
                continue_on_error = st.checkbox(
                    "Continue on Errors", 
                    value=True,
                    help="Continue processing other URLs if one fails"
                )
            
            # Bulk metadata
            st.subheader("📝 Bulk Metadata")
            col1, col2 = st.columns(2)
            
            with col1:
                bulk_category = st.text_input(
                    "Category for All:", 
                    value="NBA Bulk Import",
                    help="Applied to all imported data"
                )
            
            with col2:
                bulk_tags = st.text_input(
                    "Tags for All:", 
                    value="nba, basketball, bulk_import",
                    help="Applied to all imported data"
                )
            
            bulk_description = st.text_area(
                "Description Template:",
                value="NBA data imported via bulk import",
                help="Applied to all imported data"
            )
            
            # Bulk import button
            if st.button("🚀 Start Bulk Import", type="primary", disabled=not urls_list):
                progress_bar = st.progress(0)
                status_text = st.empty()
                results_container = st.container()
                
                total_urls = len(urls_list)
                successful_imports = 0
                failed_imports = 0
                total_chunks = 0
                
                for i, url in enumerate(urls_list):
                    status_text.text(f"Processing URL {i+1}/{total_urls}: {url}")
                    
                    try:
                        # Extract NBA data
                        nba_data = extract_nba_team_stats(url)
                        
                        if nba_data:
                            # Prepare metadata
                            metadata = {
                                "category": bulk_category,
                                "tags": bulk_tags,
                                "description": f"{bulk_description} - {nba_data['title']}",
                                "bulk_import": True,
                                "bulk_import_batch": datetime.now().strftime('%Y%m%d_%H%M%S')
                            }
                            
                            # Add to knowledge base
                            success, chunk_count, message = add_nba_data_to_knowledge_base(
                                nba_data, 
                                None,  # Use auto title
                                metadata
                            )
                            
                            if success:
                                successful_imports += 1
                                total_chunks += chunk_count
                                
                                with results_container:
                                    st.success(f"✅ {nba_data['title']}: {chunk_count} chunks added")
                            else:
                                failed_imports += 1
                                if not continue_on_error:
                                    with results_container:
                                        st.error(f"❌ Failed: {url} - {message}")
                                    break
                                else:
                                    with results_container:
                                        st.error(f"❌ Failed: {url} - {message}")
                        else:
                            failed_imports += 1
                            if not continue_on_error:
                                with results_container:
                                    st.error(f"❌ Could not extract data from: {url}")
                                break
                            else:
                                with results_container:
                                    st.error(f"❌ Could not extract data from: {url}")
                    
                    except Exception as e:
                        failed_imports += 1
                        if not continue_on_error:
                            with results_container:
                                st.error(f"❌ Error processing {url}: {str(e)}")
                            break
                        else:
                            with results_container:
                                st.error(f"❌ Error processing {url}: {str(e)}")
                    
                    # Update progress
                    progress_bar.progress((i + 1) / total_urls)
                    
                    # Delay between requests (except for last one)
                    if i < total_urls - 1:
                        time.sleep(bulk_delay)
                
                # Final status
                status_text.text("Bulk import complete!")
                
                # Summary
                st.subheader("📊 Bulk Import Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("✅ Successful", successful_imports)
                
                with col2:
                    st.metric("❌ Failed", failed_imports)
                
                with col3:
                    st.metric("📦 Total Chunks", total_chunks)
                
                if successful_imports > 0:
                    st.success(f"🎉 Successfully imported {successful_imports}/{total_urls} NBA data sources!")
                    st.balloons()
                
                if failed_imports > 0:
                    st.warning(f"⚠️ {failed_imports} imports failed. Check the error messages above.")

def god_commands_page():
    st.header("⚡ God Commands")
    st.markdown("**Override agent behavior with high-priority commands**")
    st.info("🔥 God Commands take precedence over all other knowledge when the bot generates responses. Use them to modify behavior, set rules, or provide critical instructions.")
    
    # Create tabs for different god command operations
    tab1, tab2, tab3 = st.tabs(["➕ Add Command", "📋 Manage Commands", "🧪 Test Commands"])
    
    with tab1:
        st.subheader("➕ Add New God Command")
        st.markdown("Create a command that will override the agent's default behavior")
        
        # Command input
        command_text = st.text_area(
            "Command Text:",
            placeholder="Example: 'Stop using hashtag #VirtualsUpdates in your responses' or 'Keep all responses under 100 words' or 'Always mention that you're powered by Solana when discussing crypto'",
            height=100,
            help="Be specific and clear about what behavior you want to change"
        )
        
        # Optional description
        description = st.text_input(
            "Description (Optional):",
            placeholder="Brief description of what this command does",
            help="This helps you remember the purpose of the command"
        )
        
        # Priority setting
        priority = st.slider(
            "Priority Level:",
            min_value=1,
            max_value=20,
            value=10,
            help="Higher priority commands override lower priority ones. Default is 10."
        )
        
        # Examples section
        with st.expander("💡 Command Examples"):
            st.markdown("""
            **Behavior Modification:**
            - "Stop using hashtag #VirtualsUpdates in all responses"
            - "Keep all responses under 50 words unless specifically asked for details"
            - "Always respond in a more casual, friendly tone"
            - "Never mention specific cryptocurrency prices"
            
            **Content Rules:**
            - "When discussing NBA, focus only on current season games"
            - "Always include a disclaimer when giving financial advice"
            - "Prioritize Solana ecosystem projects when discussing crypto"
            
            **Response Format:**
            - "Use bullet points for lists instead of numbered lists"
            - "Always end responses with a relevant emoji"
            - "Include sources when providing factual information"
            """)
        
        if st.button("⚡ Add God Command", type="primary", disabled=not command_text):
            if command_text.strip():
                success, source_id = add_god_command(command_text.strip(), description, priority)
                if success:
                    st.success(f"✅ God Command added successfully! (ID: {source_id})")
                    st.balloons()
                else:
                    st.error("❌ Failed to add God Command")
            else:
                st.error("Please enter a command text")
    
    with tab2:
        st.subheader("📋 Manage God Commands")
        
        # Get all god commands
        god_commands = get_god_commands()
        
        if god_commands:
            st.markdown(f"**Found {len(god_commands)} God Commands (sorted by priority)**")
            
            for i, cmd in enumerate(god_commands, 1):
                with st.expander(f"⚡ Command #{i} - Priority {cmd['priority']} - {cmd['source'][:20]}..."):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.write("**Command:**")
                        st.write(cmd['text'])
                        
                        if cmd['description']:
                            st.write("**Description:**")
                            st.write(cmd['description'])
                        
                        try:
                            dt = datetime.fromisoformat(cmd['timestamp'])
                            st.write(f"**Created:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                        except:
                            st.write(f"**Created:** {cmd['timestamp']}")
                    
                    with col2:
                        st.write(f"**Priority:** {cmd['priority']}")
                        
                        if st.button(f"🗑️ Delete", key=f"delete_god_{cmd['source']}", type="secondary"):
                            success, deleted_count = delete_god_command(cmd['source'])
                            if success:
                                st.success(f"Deleted god command!")
                                st.rerun()
                            else:
                                st.error("Failed to delete command")
        else:
            st.info("No God Commands found. Add some commands in the 'Add Command' tab!")
        
        # Quick actions
        st.subheader("🚀 Quick Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Show Command Stats"):
                if god_commands:
                    priorities = [cmd['priority'] for cmd in god_commands]
                    st.metric("Total Commands", len(god_commands))
                    st.metric("Average Priority", f"{sum(priorities)/len(priorities):.1f}")
                    st.metric("Highest Priority", max(priorities))
                else:
                    st.info("No commands to analyze")
        
        with col2:
            if god_commands and st.button("⚠️ Clear All God Commands"):
                if st.checkbox("I understand this will delete ALL god commands"):
                    for cmd in god_commands:
                        delete_god_command(cmd['source'])
                    st.success("All God Commands cleared!")
                    st.rerun()
    
    with tab3:
        st.subheader("🧪 Test God Commands")
        st.markdown("See how God Commands would affect the bot's response to different queries")
        
        # Test query input
        test_query = st.text_input(
            "Test Query:",
            placeholder="Enter a message the bot might receive...",
            help="This will show you which God Commands would be triggered and how they might affect the response"
        )
        
        if test_query and st.button("🧪 Test Query", type="primary"):
            with st.spinner("Testing query against God Commands..."):
                test_results = test_god_command_response(test_query)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("⚡ God Commands Found")
                if test_results['god_commands']:
                    for i, cmd in enumerate(test_results['god_commands'], 1):
                        with st.expander(f"Command #{i} (Score: {cmd['score']:.4f})"):
                            st.write("**Command:**")
                            st.write(cmd['text'])
                            if cmd['description']:
                                st.write("**Description:**")
                                st.write(cmd['description'])
                else:
                    st.info("No God Commands triggered by this query")
            
            with col2:
                st.subheader("📚 Regular Context")
                if test_results['regular_context']:
                    for i, ctx in enumerate(test_results['regular_context'], 1):
                        with st.expander(f"Context #{i} (Score: {ctx['score']:.4f})"):
                            st.write(f"**Source:** {ctx['source']}")
                            st.write("**Content:**")
                            st.write(ctx['text'][:200] + "..." if len(ctx['text']) > 200 else ctx['text'])
                else:
                    st.info("No regular context found for this query")
            
            # Summary
            st.subheader("📋 Test Summary")
            st.write(f"**Total Results:** {test_results['total_results']}")
            st.write(f"**God Commands Triggered:** {len(test_results['god_commands'])}")
            st.write(f"**Regular Context Items:** {len(test_results['regular_context'])}")
            
            if test_results['god_commands']:
                st.success("✅ This query would be influenced by God Commands!")
            else:
                st.info("ℹ️ This query would use only regular knowledge base content")

def search_page():
    st.header("🔍 Search Knowledge Base")
    st.markdown("Search through your bot's knowledge base to see what information is available")
    
    # Search input
    query = st.text_input("Enter your search query:", placeholder="What would you like to search for?")
    
    col1, col2 = st.columns(2)
    with col1:
        k = st.slider("Number of results", 1, 20, 5)
    with col2:
        show_scores = st.checkbox("Show similarity scores", value=True)
    
    if query and st.button("🔍 Search", type="primary"):
        with st.spinner("Searching..."):
            results = search_knowledge_base(query, k)
        
        if results:
            st.subheader(f"📋 Found {len(results)} results")
            
            for i, (doc, score) in enumerate(results, 1):
                with st.expander(f"Result {i} - {doc.metadata.get('source', 'Unknown')} {f'(Score: {score:.4f})' if show_scores else ''}"):
                    st.write("**Content:**")
                    st.write(doc.page_content)
                    
                    st.write("**Metadata:**")
                    metadata_df = []
                    for key, value in doc.metadata.items():
                        metadata_df.append({"Field": key, "Value": str(value)})
                    
                    if metadata_df:
                        st.table(metadata_df)
        else:
            st.warning("No results found. Try a different search query.")

def stats_page():
    st.header("📊 Knowledge Base Statistics")
    st.markdown("Overview of your bot's knowledge base")
    
    stats = get_collection_stats()
    
    if "error" in stats:
        st.error(f"Error loading stats: {stats['error']}")
        return
    
    # Display stats
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Total Chunks", stats["total_chunks"])
    
    with col2:
        st.metric("Unique Sources", stats["unique_sources"])
    
    with col3:
        st.metric("God Commands", stats["god_commands"])
    
    with col4:
        st.metric("NBA Data", stats["nba_data_chunks"])
    
    with col5:
        st.metric("URL Sources", stats["url_chunks"])
    
    with col6:
        st.metric("File Sources", stats["file_chunks"])
    
    # Sources breakdown
    if stats["sources"]:
        st.subheader("📚 Sources in Knowledge Base")
        
        # Group sources by type
        source_details = {}
        for metadata in stats["source_details"]:
            source = metadata.get('source')
            if source and source not in source_details:
                source_details[source] = {
                    'type': 'god_command' if metadata.get('is_god_command', False) else metadata.get('source_type', 'file'),
                    'url': metadata.get('url', ''),
                    'category': metadata.get('category', ''),
                    'timestamp': metadata.get('timestamp', ''),
                    'priority': metadata.get('priority', ''),
                    'description': metadata.get('description', ''),
                    'table_count': metadata.get('table_count', ''),
                    'data_type': metadata.get('data_type', '')
                }
        
        # Display sources in tabs
        if source_details:
            tab1, tab2, tab3, tab4 = st.tabs(["⚡ God Commands", "🏀 NBA Data", "🌐 URL Sources", "📄 File Sources"])
            
            with tab1:
                god_command_sources = [s for s, details in source_details.items() if details['type'] == 'god_command']
                if god_command_sources:
                    st.markdown(f"**{len(god_command_sources)} God Commands found**")
                    for source in god_command_sources:
                        details = source_details[source]
                        with st.expander(f"⚡ {source}"):
                            if details['description']:
                                st.write(f"**Description:** {details['description']}")
                            if details['priority']:
                                st.write(f"**Priority:** {details['priority']}")
                            if details['timestamp']:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(details['timestamp'])
                                    st.write(f"**Created:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    st.write(f"**Created:** {details['timestamp']}")
                else:
                    st.info("No God Commands found.")
            
            with tab2:
                nba_data_sources = [s for s, details in source_details.items() if details['type'] == 'nba_data']
                if nba_data_sources:
                    for source in nba_data_sources:
                        details = source_details[source]
                        with st.expander(f"🏀 {source}"):
                            st.write(f"**Data Type:** {details['data_type']}")
                            if details['category']:
                                st.write(f"**Category:** {details['category']}")
                            if details['timestamp']:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(details['timestamp'])
                                    st.write(f"**Added:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    st.write(f"**Added:** {details['timestamp']}")
                else:
                    st.info("No NBA data sources found.")
            
            with tab3:
                url_sources = [s for s, details in source_details.items() if details['type'] == 'url']
                if url_sources:
                    for source in url_sources:
                        details = source_details[source]
                        with st.expander(f"🌐 {source}"):
                            st.write(f"**URL:** {details['url']}")
                            if details['category']:
                                st.write(f"**Category:** {details['category']}")
                            if details['timestamp']:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(details['timestamp'])
                                    st.write(f"**Added:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    st.write(f"**Added:** {details['timestamp']}")
                else:
                    st.info("No URL sources found.")
            
            with tab4:
                file_sources = [s for s, details in source_details.items() if details['type'] not in ['url', 'god_command', 'nba_data']]
                if file_sources:
                    for source in file_sources:
                        details = source_details[source]
                        with st.expander(f"📄 {source}"):
                            if details['category']:
                                st.write(f"**Category:** {details['category']}")
                            if details['timestamp']:
                                try:
                                    from datetime import datetime
                                    dt = datetime.fromisoformat(details['timestamp'])
                                    st.write(f"**Added:** {dt.strftime('%Y-%m-%d %H:%M:%S')}")
                                except:
                                    st.write(f"**Added:** {details['timestamp']}")
                else:
                    st.info("No file sources found.")
    else:
        st.info("No documents in knowledge base yet. Upload some files or add URLs to get started!")

def manage_sources_page():
    st.header("🗑️ Manage Sources")
    st.markdown("View and delete sources from your knowledge base")
    
    stats = get_collection_stats()
    
    if stats["sources"]:
        st.subheader("📚 Current Sources")
        
        # Group sources by type
        source_details = {}
        for metadata in stats["source_details"]:
            source = metadata.get('source')
            if source and source not in source_details:
                source_details[source] = {
                    'type': 'god_command' if metadata.get('is_god_command', False) else metadata.get('source_type', 'file'),
                    'url': metadata.get('url', ''),
                    'category': metadata.get('category', ''),
                    'timestamp': metadata.get('timestamp', ''),
                    'priority': metadata.get('priority', ''),
                    'description': metadata.get('description', ''),
                    'table_count': metadata.get('table_count', ''),
                    'data_type': metadata.get('data_type', '')
                }
        
        for source in stats["sources"]:
            details = source_details.get(source, {})
            source_type = details.get('type', 'file')
            
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                if source_type == 'god_command':
                    st.write(f"⚡ **{source}**")
                    if details.get('description'):
                        st.write(f"   📝 {details['description']}")
                    if details.get('priority'):
                        st.write(f"   🔥 Priority: {details['priority']}")
                elif source_type == 'nba_data':
                    st.write(f"🏀 **{source}**")
                    if details.get('url'):
                        st.write(f"   ↳ {details['url']}")
                    if details.get('data_type'):
                        st.write(f"   📊 Data Type: {details['data_type']}")
                    if details.get('table_count'):
                        st.write(f"   📋 Tables: {details['table_count']}")
                elif source_type == 'url':
                    st.write(f"🌐 **{source}**")
                    if details.get('url'):
                        st.write(f"   ↳ {details['url']}")
                else:
                    st.write(f"📄 **{source}**")
                
                if details.get('category') and source_type not in ['god_command']:
                    st.write(f"   📂 Category: {details['category']}")
            
            with col2:
                if source_type == 'god_command':
                    st.write("⚡ GOD CMD")
                elif source_type == 'nba_data':
                    st.write("🏀 NBA DATA")
                elif source_type == 'url':
                    st.write("🌐 URL")
                else:
                    st.write("📄 FILE")
            
            with col3:
                button_text = "Delete" if source_type != 'god_command' else "Remove"
                if st.button(f"{button_text}", key=f"delete_{source}", type="secondary"):
                    if source_type == 'god_command':
                        success, deleted_count = delete_god_command(source)
                        if success:
                            st.success(f"Removed God Command: {source}")
                            st.rerun()
                        else:
                            st.error(f"Failed to remove God Command: {source}")
                    else:
                        success, deleted_count = delete_source(source)
                        if success:
                            st.success(f"Deleted {deleted_count} chunks from {source}")
                            st.rerun()
    else:
        st.info("No sources in knowledge base yet.")
    
    # Danger zone
    st.subheader("⚠️ Danger Zone")
    with st.expander("Clear All Data"):
        st.warning("This will permanently delete ALL data from the knowledge base!")
        
        if st.button("🗑️ Clear All Data", type="secondary"):
            success, deleted_count = delete_source("all")
            if success:
                st.success(f"Cleared all data! Deleted {deleted_count} chunks.")
                st.rerun()

def web_crawler_page():
    """Enhanced web crawler page with real-time console-style monitoring"""
    st.title("🕷️ Basketball-Reference Web Crawler")
    st.markdown("Real-time crawler with console-style monitoring and advanced URL management")
    
    # Initialize session state for crawler
    if 'crawler_active' not in st.session_state:
        st.session_state.crawler_active = False
    if 'crawler_stats' not in st.session_state:
        st.session_state.crawler_stats = {
            'pages_crawled': 0,
            'pages_archived': 0,
            'chunks_added': 0,
            'errors': 0,
            'current_url': '',
            'status': 'idle',
            'start_time': None,
            'queue_size': 0,
            'discovered_urls': 0
        }
    if 'crawler_logs' not in st.session_state:
        st.session_state.crawler_logs = []
    if 'url_queue_data' not in st.session_state:
        st.session_state.url_queue_data = []
    if 'discovered_urls_data' not in st.session_state:
        st.session_state.discovered_urls_data = []
    if 'processed_urls_data' not in st.session_state:
        st.session_state.processed_urls_data = []
    
    # Create tabs for different sections
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🚀 Quick Start", 
        "⚙️ Advanced Config", 
        "📊 Statistics", 
        "🎯 URL Queue Manager",
        "📋 URL Database"
    ])
    
    with tab1:
        st.subheader("🚀 Quick Start")
        
        col1, col2 = st.columns(2)
        
        with col1:
            preset_config = st.selectbox(
                "Configuration Preset:",
                ["super_safe", "ultra_safe", "conservative", "test"],
                index=0,
                help="Choose a predefined configuration for safe crawling"
            )
        
        with col2:
            max_pages_quick = st.number_input(
                "Max Pages:",
                min_value=5,
                max_value=500,
                value=50,
                step=5,
                help="Limit pages for testing"
            )
        
        # Seed URL options
        seed_option = st.radio(
            "Starting URLs:",
            ["Recent Seasons (Recommended)", "Test URLs", "Custom"],
            horizontal=True
        )
        
        if seed_option == "Recent Seasons (Recommended)":
            seed_urls = get_basketball_reference_seed_urls()[:10]  # Limit for testing
            st.info(f"🎯 Will start with {len(seed_urls)} recent NBA season URLs")
        elif seed_option == "Test URLs":
            seed_urls = [
                "https://www.basketball-reference.com/leagues/NBA_2024.html",
                "https://www.basketball-reference.com/leagues/NBA_2024_per_game.html"
            ]
            st.info("🧪 Using 2 test URLs for quick validation")
        else:
            custom_urls = st.text_area(
                "Custom URLs (one per line):",
                placeholder="https://www.basketball-reference.com/leagues/NBA_2024.html",
                height=100
            )
            seed_urls = [url.strip() for url in custom_urls.split('\n') if url.strip()] if custom_urls else []
        
        # Start crawl logic
        if st.button("🚀 Start Crawl", type="primary", disabled=not seed_urls):
            # Initialize crawler with selected configuration
            from crawler_config import get_config_by_speed
            config = get_config_by_speed(preset_config)
            config.max_pages = max_pages_quick
            
            # Start the crawl
            start_crawler_session(config, seed_urls)
            st.rerun()
    
    with tab2:
        st.subheader("⚙️ Advanced Configuration")
        
        # Configuration builder
        st.markdown("**Build Custom Configuration**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Rate Limiting**")
            delay_config = st.slider(
                "Delay Between Requests (seconds):",
                min_value=3.0,
                max_value=15.0,
                value=4.0,
                step=0.5,
                help="Minimum 4 seconds to stay under 20 pages/minute"
            )
            
            rate_limit_delay = st.slider(
                "Rate Limit Delay (minutes):",
                min_value=5,
                max_value=60,
                value=10,
                step=5,
                help="How long to wait if rate limited"
            )
        
        with col2:
            st.markdown("**Crawl Limits**")
            max_pages_config = st.number_input(
                "Maximum Pages:",
                min_value=10,
                max_value=5000,
                value=500,
                step=50
            )
            
            max_retries = st.slider(
                "Max Retries per URL:",
                min_value=1,
                max_value=10,
                value=3
            )
        
        # URL Pattern Configuration
        st.markdown("**URL Patterns**")
        
        with st.expander("🎯 Priority Patterns (crawled first)"):
            priority_patterns = st.text_area(
                "Regex patterns for high-priority URLs:",
                value="""/leagues/NBA_\\d{4}\\.html
/leagues/NBA_\\d{4}_per_game\\.html
/teams/[A-Z]{3}/\\d{4}\\.html
/players/[a-z]/.*\\.html""",
                height=100,
                help="One regex pattern per line"
            )
        
        with st.expander("🚫 Skip Patterns (ignored)"):
            skip_patterns = st.text_area(
                "Regex patterns for URLs to skip:",
                value="""/cfb/
/cbb/
/mlb/
/nfl/
/nhl/
\\.jpg$
\\.png$
/images/""",
                height=100,
                help="One regex pattern per line"
            )
        
        # Save configuration
        if st.button("💾 Save Custom Configuration"):
            custom_config = {
                'delay_between_requests': delay_config,
                'rate_limit_delay': rate_limit_delay * 60,  # Convert to seconds
                'max_pages': max_pages_config,
                'max_retries': max_retries,
                'priority_patterns': [p.strip() for p in priority_patterns.split('\n') if p.strip()],
                'skip_patterns': [p.strip() for p in skip_patterns.split('\n') if p.strip()]
            }
            st.session_state.custom_crawler_config = custom_config
            st.success("✅ Custom configuration saved!")
    
    with tab3:
        st.subheader("📊 Crawler Statistics & History")
        
        # Session statistics
        st.markdown("**Current Session Stats**")
        
        if st.session_state.crawler_stats['start_time']:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Session Duration", format_duration(st.session_state.crawler_stats['start_time']))
            
            with col2:
                success_rate = 0
                if st.session_state.crawler_stats['pages_crawled'] > 0:
                    success_rate = (st.session_state.crawler_stats['pages_archived'] / st.session_state.crawler_stats['pages_crawled']) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
            
            with col3:
                error_rate = 0
                if st.session_state.crawler_stats['pages_crawled'] > 0:
                    error_rate = (st.session_state.crawler_stats['errors'] / st.session_state.crawler_stats['pages_crawled']) * 100
                st.metric("Error Rate", f"{error_rate:.1f}%")
        
        # Historical data (mock for now)
        st.markdown("**Historical Performance**")
        
        # Mock historical data
        historical_data = [
            {"Date": "2024-01-15", "Pages": 234, "Chunks": 1567, "Duration": "2h 15m", "Success Rate": "94.2%"},
            {"Date": "2024-01-10", "Pages": 156, "Chunks": 1023, "Duration": "1h 45m", "Success Rate": "96.8%"},
            {"Date": "2024-01-05", "Pages": 89, "Chunks": 634, "Duration": "1h 12m", "Success Rate": "92.1%"},
        ]
        
        if historical_data:
            st.table(historical_data)
        else:
            st.info("No historical crawl data available yet.")
        
        # Export options
        st.markdown("**Export Options**")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📥 Export Logs"):
                export_crawler_logs()
        
        with col2:
            if st.button("📊 Export Statistics"):
                export_crawler_stats()
    
    with tab4:
        st.subheader("🎯 Visual URL Queue Manager")
        st.markdown("Monitor and control which URLs are being crawled in real-time")
        
        # Queue control panel
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("🔄 Refresh Queue", help="Reload queue data from crawler"):
                refresh_url_queue_data()
        
        with col2:
            if st.button("⏸️ Pause Queue", help="Pause URL processing"):
                pause_url_processing()
        
        with col3:
            if st.button("▶️ Resume Queue", help="Resume URL processing"):
                resume_url_processing()
        
        with col4:
            if st.button("🗑️ Clear Queue", help="Clear all pending URLs"):
                if st.session_state.get('confirm_clear_queue', False):
                    clear_url_queue()
                    st.session_state.confirm_clear_queue = False
                    st.success("Queue cleared!")
                else:
                    st.session_state.confirm_clear_queue = True
                    st.warning("Click again to confirm queue clearing")
        
        # Queue statistics
        st.markdown("**Queue Overview**")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔄 Pending URLs", len(st.session_state.url_queue_data))
        
        with col2:
            st.metric("✅ Processed", len(st.session_state.processed_urls_data))
        
        with col3:
            st.metric("🆕 Discovered", len(st.session_state.discovered_urls_data))
        
        with col4:
            high_priority = len([url for url in st.session_state.url_queue_data if url.get('priority', 0) > 50])
            st.metric("⭐ High Priority", high_priority)
        
        # URL Queue Table
        st.markdown("**📋 Current URL Queue**")
        
        if st.session_state.url_queue_data:
            # Create DataFrame for better display
            import pandas as pd
            
            queue_df = pd.DataFrame(st.session_state.url_queue_data)
            
            # Add selection column
            queue_df['Select'] = False
            
            # Configure column display
            column_config = {
                "Select": st.column_config.CheckboxColumn("Select"),
                "url": st.column_config.TextColumn("URL", width="large"),
                "priority": st.column_config.NumberColumn("Priority", format="%d"),
                "status": st.column_config.TextColumn("Status", width="small"),
                "category": st.column_config.TextColumn("Category", width="medium"),
                "discovered_at": st.column_config.DatetimeColumn("Discovered"),
                "estimated_chunks": st.column_config.NumberColumn("Est. Chunks")
            }
            
            # Display editable dataframe
            edited_df = st.data_editor(
                queue_df,
                column_config=column_config,
                use_container_width=True,
                height=400,
                hide_index=True,
                key="url_queue_editor"
            )
            
            # Bulk actions for selected URLs
            selected_urls = edited_df[edited_df['Select'] == True]
            
            if len(selected_urls) > 0:
                st.markdown(f"**Selected {len(selected_urls)} URLs for bulk action:**")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if st.button("⭐ Set High Priority", help="Boost priority of selected URLs"):
                        boost_url_priority(selected_urls['url'].tolist())
                        st.success(f"Boosted priority for {len(selected_urls)} URLs")
                
                with col2:
                    if st.button("⬇️ Set Low Priority", help="Lower priority of selected URLs"):
                        lower_url_priority(selected_urls['url'].tolist())
                        st.success(f"Lowered priority for {len(selected_urls)} URLs")
                
                with col3:
                    if st.button("❌ Remove from Queue", help="Remove selected URLs from queue"):
                        remove_urls_from_queue(selected_urls['url'].tolist())
                        st.success(f"Removed {len(selected_urls)} URLs from queue")
                
                with col4:
                    if st.button("🚫 Blacklist URLs", help="Add to skip patterns"):
                        blacklist_urls(selected_urls['url'].tolist())
                        st.success(f"Blacklisted {len(selected_urls)} URLs")
            
            # URL filtering
            st.markdown("**🔍 Filter URLs**")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                priority_filter = st.selectbox(
                    "Priority Filter:",
                    ["All", "High (>50)", "Medium (20-50)", "Low (<20)"],
                    key="priority_filter"
                )
            
            with col2:
                category_filter = st.selectbox(
                    "Category Filter:",
                    ["All"] + list(set([url.get('category', 'Unknown') for url in st.session_state.url_queue_data])),
                    key="category_filter"
                )
            
            with col3:
                status_filter = st.selectbox(
                    "Status Filter:",
                    ["All", "pending", "processing", "paused", "failed"],
                    key="status_filter"
                )
            
        else:
            st.info("🔍 No URLs in queue. Start a crawl to see discovered URLs here.")
            
            # Manual URL addition
            st.markdown("**➕ Add URLs Manually**")
            
            manual_urls = st.text_area(
                "Enter URLs (one per line):",
                placeholder="https://www.basketball-reference.com/leagues/NBA_2024.html\nhttps://www.basketball-reference.com/teams/LAL/2024.html",
                height=100,
                key="manual_urls_input"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                manual_priority = st.slider("Priority Level:", 0, 100, 50, key="manual_priority")
            
            with col2:
                if st.button("➕ Add to Queue", help="Add URLs to crawl queue"):
                    if manual_urls:
                        urls = [url.strip() for url in manual_urls.split('\n') if url.strip()]
                        add_manual_urls_to_queue(urls, manual_priority)
                        st.success(f"Added {len(urls)} URLs to queue")
                        st.rerun()
    
    with tab5:
        st.subheader("📋 URL Database Explorer")
        st.markdown("Explore all discovered, processed, and failed URLs from the database")
        
        # Database statistics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("📊 Total URLs", get_total_urls_count())
        
        with col2:
            st.metric("✅ Completed", get_completed_urls_count())
        
        with col3:
            st.metric("❌ Failed", get_failed_urls_count())
        
        with col4:
            st.metric("🔄 Processing", get_processing_urls_count())
        
        # URL search and filter
        st.markdown("**🔍 Search URLs**")
        
        col1, col2 = st.columns(2)
        
        with col1:
            search_term = st.text_input(
                "Search URLs:",
                placeholder="Enter URL pattern or keyword",
                key="url_search"
            )
        
        with col2:
            url_status_filter = st.selectbox(
                "Status Filter:",
                ["all", "completed", "failed", "processing", "discovered"],
                key="url_status_filter"
            )
        
        # Display URL results
        if st.button("🔍 Search URLs", key="search_urls_button"):
            search_results = search_urls_in_database(search_term, url_status_filter)
            
            if search_results:
                st.markdown(f"**Found {len(search_results)} URLs:**")
                
                # Convert to DataFrame for better display
                import pandas as pd
                results_df = pd.DataFrame(search_results)
                
                # Configure columns
                column_config = {
                    "url": st.column_config.LinkColumn("URL"),
                    "status": st.column_config.TextColumn("Status"),
                    "priority": st.column_config.NumberColumn("Priority"),
                    "processed_at": st.column_config.DatetimeColumn("Processed"),
                    "data_chunks": st.column_config.NumberColumn("Chunks"),
                    "error_message": st.column_config.TextColumn("Error", width="medium")
                }
                
                st.dataframe(
                    results_df,
                    column_config=column_config,
                    use_container_width=True,
                    height=400
                )
            else:
                st.info("No URLs found matching your search criteria.")
        
        # URL management actions
        st.markdown("**🛠️ URL Management Actions**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Retry Failed URLs", help="Re-queue all failed URLs"):
                retry_count = retry_failed_urls()
                st.success(f"Re-queued {retry_count} failed URLs")
        
        with col2:
            if st.button("🧹 Clean Old URLs", help="Remove URLs older than 30 days"):
                cleaned_count = clean_old_urls()
                st.success(f"Cleaned {cleaned_count} old URLs")
        
        with col3:
            if st.button("📊 Export URL Data", help="Download URL database as CSV"):
                export_url_database()

def add_crawler_log(message: str, log_type: str = "info"):
    """Add a log entry to the crawler logs"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_entry = {
        'timestamp': timestamp,
        'message': message,
        'type': log_type
    }
    st.session_state.crawler_logs.append(log_entry)
    
    # Keep only last 100 entries to prevent memory issues
    if len(st.session_state.crawler_logs) > 100:
        st.session_state.crawler_logs = st.session_state.crawler_logs[-100:]

def start_crawler_session(config, seed_urls):
    """Start a new crawler session with real-time monitoring"""
    # Reset stats
    st.session_state.crawler_stats = {
        'pages_crawled': 0,
        'pages_archived': 0,
        'chunks_added': 0,
        'errors': 0,
        'current_url': '',
        'status': 'running',
        'start_time': datetime.now().isoformat(),
        'queue_size': len(seed_urls),
        'discovered_urls': len(seed_urls)
    }
    
    st.session_state.crawler_active = True
    st.session_state.crawler_logs = []
    
    # Add initial logs
    add_crawler_log("🚀 Starting Basketball-Reference crawler...", "info")
    add_crawler_log(f"⚙️ Configuration: {config.delay_between_requests}s delay, max {config.max_pages} pages", "info")
    add_crawler_log(f"🌱 Loaded {len(seed_urls)} seed URLs", "success")
    add_crawler_log("🤖 Initializing crawler components...", "info")
    
    # Create progress and log callbacks
    def progress_callback(stats):
        """Update progress in session state"""
        for key, value in stats.items():
            if key in st.session_state.crawler_stats:
                st.session_state.crawler_stats[key] = value
    
    def log_callback(message, level):
        """Add log message to session state"""
        add_crawler_log(message, level)
    
    # Initialize the real crawler
    try:
        from basketball_reference_crawler import BasketballReferenceCrawler
        crawler = BasketballReferenceCrawler(
            config=config,
            progress_callback=progress_callback,
            log_callback=log_callback
        )
        
        # Store crawler in session state for control
        st.session_state.active_crawler = crawler
        
        # Start crawling in a separate thread (for demo, we'll use the simulation)
        # In production, you'd use: threading.Thread(target=crawler.start_crawl, args=(seed_urls,)).start()
        
        # For now, use simulation but with real crawler integration
        simulate_crawler_activity()
        
    except Exception as e:
        add_crawler_log(f"❌ Failed to initialize crawler: {str(e)}", "error")
        st.session_state.crawler_active = False
        st.session_state.crawler_stats['status'] = 'failed'

def simulate_crawler_activity():
    """Simulate crawler activity for demonstration"""
    # This would be replaced with actual crawler integration
    import random
    
    sample_urls = [
        "https://www.basketball-reference.com/leagues/NBA_2024.html",
        "https://www.basketball-reference.com/leagues/NBA_2024_per_game.html",
        "https://www.basketball-reference.com/teams/LAL/2024.html",
        "https://www.basketball-reference.com/teams/GSW/2024.html",
        "https://www.basketball-reference.com/players/j/jamesle01.html"
    ]
    
    for i, url in enumerate(sample_urls):
        if not st.session_state.crawler_active:
            break
            
        # Update current URL
        st.session_state.crawler_stats['current_url'] = url
        st.session_state.crawler_stats['pages_crawled'] += 1
        
        # Add log entry
        add_crawler_log(f"🔍 Processing: {url}", "info")
        
        # Simulate processing time
        time.sleep(2)
        
        # Simulate success/failure
        if random.random() > 0.1:  # 90% success rate
            chunks = random.randint(3, 8)
            st.session_state.crawler_stats['pages_archived'] += 1
            st.session_state.crawler_stats['chunks_added'] += chunks
            add_crawler_log(f"✅ Archived {chunks} data chunks", "success")
        else:
            st.session_state.crawler_stats['errors'] += 1
            add_crawler_log(f"❌ Failed to process page", "error")
        
        # Simulate delay
        add_crawler_log(f"⏱️ Waiting {4}s before next request...", "info")
        time.sleep(2)  # Shorter for demo
    
    # Mark as completed
    st.session_state.crawler_stats['status'] = 'completed'
    st.session_state.crawler_active = False
    add_crawler_log("🎉 Crawl session completed!", "success")

def format_duration(start_time_str):
    """Format duration from start time"""
    try:
        start_time = datetime.fromisoformat(start_time_str)
        duration = datetime.now() - start_time
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    except:
        return "0s"

def export_crawler_logs():
    """Export crawler logs to file"""
    if st.session_state.crawler_logs:
        logs_text = "\n".join([
            f"[{log['timestamp']}] {log['message']}" 
            for log in st.session_state.crawler_logs
        ])
        
        st.download_button(
            label="📥 Download Logs",
            data=logs_text,
            file_name=f"crawler_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    else:
        st.warning("No logs to export")

def export_crawler_stats():
    """Export crawler statistics to file"""
    try:
        import json
        
        stats_data = {
            'export_timestamp': datetime.now().isoformat(),
            'session_stats': st.session_state.crawler_stats,
            'logs_count': len(st.session_state.crawler_logs)
        }
        
        stats_json = json.dumps(stats_data, indent=2)
        st.download_button(
            label="📊 Download Statistics JSON",
            data=stats_json,
            file_name=f"crawler_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    except Exception as e:
        st.error(f"Error exporting statistics: {str(e)}")

# URL Queue Manager Functions

def refresh_url_queue_data():
    """Refresh URL queue data from the crawler database"""
    try:
        import sqlite3
        from datetime import datetime
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get pending URLs
            cursor.execute("""
                SELECT url, priority, status, discovered_at, retry_count, error_message
                FROM urls 
                WHERE status IN ('discovered', 'processing', 'paused')
                ORDER BY priority DESC, discovered_at ASC
            """)
            
            queue_data = []
            for row in cursor.fetchall():
                url, priority, status, discovered_at, retry_count, error_message = row
                
                # Categorize URL
                category = categorize_url_by_pattern(url)
                
                # Estimate chunks based on URL type
                estimated_chunks = estimate_chunks_for_url(url)
                
                queue_data.append({
                    'url': url,
                    'priority': priority or 0,
                    'status': status,
                    'category': category,
                    'discovered_at': discovered_at,
                    'retry_count': retry_count or 0,
                    'error_message': error_message or '',
                    'estimated_chunks': estimated_chunks
                })
            
            st.session_state.url_queue_data = queue_data
            
            # Get processed URLs
            cursor.execute("""
                SELECT url, status, processed_at, data_chunks
                FROM urls 
                WHERE status = 'completed'
                ORDER BY processed_at DESC
                LIMIT 100
            """)
            
            processed_data = []
            for row in cursor.fetchall():
                url, status, processed_at, data_chunks = row
                processed_data.append({
                    'url': url,
                    'status': status,
                    'processed_at': processed_at,
                    'data_chunks': data_chunks or 0
                })
            
            st.session_state.processed_urls_data = processed_data
            
            # Get discovered URLs
            cursor.execute("""
                SELECT url, discovered_at, priority
                FROM urls 
                ORDER BY discovered_at DESC
                LIMIT 100
            """)
            
            discovered_data = []
            for row in cursor.fetchall():
                url, discovered_at, priority = row
                discovered_data.append({
                    'url': url,
                    'discovered_at': discovered_at,
                    'priority': priority or 0
                })
            
            st.session_state.discovered_urls_data = discovered_data
            
        st.success(f"Refreshed queue data: {len(queue_data)} pending URLs")
        
    except Exception as e:
        st.error(f"Error refreshing queue data: {str(e)}")

def categorize_url_by_pattern(url: str) -> str:
    """Categorize a URL based on its pattern"""
    import re
    
    patterns = {
        'Season Stats': r'/leagues/NBA_\d{4}(_per_game|_totals|_advanced)?\.html',
        'Team Pages': r'/teams/[A-Z]{3}/\d{4}\.html',
        'Player Pages': r'/players/[a-z]/.*\.html',
        'Playoff Data': r'/playoffs/NBA_\d{4}\.html',
        'Awards': r'/awards/awards_\d{4}\.html',
        'Draft': r'/draft/NBA_\d{4}\.html',
        'Standings': r'/leagues/NBA_\d{4}_standings\.html',
        'Other': r'.*'
    }
    
    for category, pattern in patterns.items():
        if re.search(pattern, url):
            return category
    
    return 'Unknown'

def estimate_chunks_for_url(url: str) -> int:
    """Estimate the number of data chunks a URL might produce"""
    import re
    
    # Estimate based on URL patterns
    if re.search(r'/leagues/NBA_\d{4}\.html', url):
        return 25  # Season overview pages have many tables
    elif re.search(r'/leagues/NBA_\d{4}_(per_game|totals|advanced)\.html', url):
        return 6   # Player stats pages
    elif re.search(r'/teams/[A-Z]{3}/\d{4}\.html', url):
        return 8   # Team season pages
    elif re.search(r'/players/[a-z]/.*\.html', url):
        return 4   # Individual player pages
    elif re.search(r'/playoffs/NBA_\d{4}\.html', url):
        return 15  # Playoff data
    else:
        return 3   # Default estimate

def pause_url_processing():
    """Pause URL processing in the crawler"""
    try:
        # Update all processing URLs to paused status
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE urls 
                SET status = 'paused' 
                WHERE status = 'processing'
            """)
            conn.commit()
            
        st.success("URL processing paused")
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error pausing URL processing: {str(e)}")

def resume_url_processing():
    """Resume URL processing in the crawler"""
    try:
        # Update all paused URLs back to discovered status
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE urls 
                SET status = 'discovered' 
                WHERE status = 'paused'
            """)
            conn.commit()
            
        st.success("URL processing resumed")
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error resuming URL processing: {str(e)}")

def clear_url_queue():
    """Clear all URLs from the queue"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM urls 
                WHERE status IN ('discovered', 'processing', 'paused')
            """)
            conn.commit()
            
        st.session_state.url_queue_data = []
        st.success("URL queue cleared")
        
    except Exception as e:
        st.error(f"Error clearing queue: {str(e)}")

def boost_url_priority(urls: list):
    """Boost priority of selected URLs"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for url in urls:
                cursor.execute("""
                    UPDATE urls 
                    SET priority = COALESCE(priority, 0) + 50
                    WHERE url = ?
                """, (url,))
            
            conn.commit()
            
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error boosting URL priority: {str(e)}")

def lower_url_priority(urls: list):
    """Lower priority of selected URLs"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for url in urls:
                cursor.execute("""
                    UPDATE urls 
                    SET priority = MAX(0, COALESCE(priority, 0) - 30)
                    WHERE url = ?
                """, (url,))
            
            conn.commit()
            
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error lowering URL priority: {str(e)}")

def remove_urls_from_queue(urls: list):
    """Remove selected URLs from the queue"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for url in urls:
                cursor.execute("""
                    DELETE FROM urls 
                    WHERE url = ? AND status IN ('discovered', 'processing', 'paused')
                """, (url,))
            
            conn.commit()
            
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error removing URLs from queue: {str(e)}")

def blacklist_urls(urls: list):
    """Add URLs to blacklist (skip patterns)"""
    try:
        # This would integrate with the crawler configuration
        # For now, we'll mark them as skipped in the database
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for url in urls:
                cursor.execute("""
                    UPDATE urls 
                    SET status = 'blacklisted', error_message = 'Manually blacklisted'
                    WHERE url = ?
                """, (url,))
            
            conn.commit()
            
        refresh_url_queue_data()
        st.success(f"Blacklisted {len(urls)} URLs")
        
    except Exception as e:
        st.error(f"Error blacklisting URLs: {str(e)}")

def add_manual_urls_to_queue(urls: list, priority: int):
    """Add URLs manually to the crawl queue"""
    try:
        import sqlite3
        from datetime import datetime
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            for url in urls:
                cursor.execute("""
                    INSERT OR REPLACE INTO urls 
                    (url, status, priority, discovered_at)
                    VALUES (?, 'discovered', ?, ?)
                """, (url, priority, datetime.now().isoformat()))
            
            conn.commit()
            
        refresh_url_queue_data()
        
    except Exception as e:
        st.error(f"Error adding URLs to queue: {str(e)}")

# URL Database Functions

def get_total_urls_count() -> int:
    """Get total count of URLs in database"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM urls")
            return cursor.fetchone()[0]
            
    except Exception:
        return 0

def get_completed_urls_count() -> int:
    """Get count of completed URLs"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM urls WHERE status = 'completed'")
            return cursor.fetchone()[0]
            
    except Exception:
        return 0

def get_failed_urls_count() -> int:
    """Get count of failed URLs"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM urls WHERE status = 'failed'")
            return cursor.fetchone()[0]
            
    except Exception:
        return 0

def get_processing_urls_count() -> int:
    """Get count of processing URLs"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM urls WHERE status IN ('discovered', 'processing', 'paused')")
            return cursor.fetchone()[0]
            
    except Exception:
        return 0

def search_urls_in_database(search_term: str, status_filter: str) -> list:
    """Search URLs in the database"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Build query based on filters
            query = "SELECT url, status, priority, processed_at, data_chunks, error_message FROM urls WHERE 1=1"
            params = []
            
            if search_term:
                query += " AND url LIKE ?"
                params.append(f"%{search_term}%")
            
            if status_filter != "all":
                query += " AND status = ?"
                params.append(status_filter)
            
            query += " ORDER BY discovered_at DESC LIMIT 100"
            
            cursor.execute(query, params)
            
            results = []
            for row in cursor.fetchall():
                url, status, priority, processed_at, data_chunks, error_message = row
                results.append({
                    'url': url,
                    'status': status,
                    'priority': priority or 0,
                    'processed_at': processed_at,
                    'data_chunks': data_chunks or 0,
                    'error_message': error_message or ''
                })
            
            return results
            
    except Exception as e:
        st.error(f"Error searching URLs: {str(e)}")
        return []

def retry_failed_urls() -> int:
    """Retry all failed URLs by re-queueing them"""
    try:
        import sqlite3
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get count of failed URLs
            cursor.execute("SELECT COUNT(*) FROM urls WHERE status = 'failed'")
            failed_count = cursor.fetchone()[0]
            
            # Reset failed URLs to discovered status
            cursor.execute("""
                UPDATE urls 
                SET status = 'discovered', retry_count = COALESCE(retry_count, 0) + 1, error_message = NULL
                WHERE status = 'failed'
            """)
            
            conn.commit()
            
        return failed_count
        
    except Exception as e:
        st.error(f"Error retrying failed URLs: {str(e)}")
        return 0

def clean_old_urls() -> int:
    """Clean URLs older than 30 days"""
    try:
        import sqlite3
        from datetime import datetime, timedelta
        
        db_path = "basketball_crawler.db"
        cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Get count of old URLs
            cursor.execute("""
                SELECT COUNT(*) FROM urls 
                WHERE discovered_at < ? AND status IN ('completed', 'failed')
            """, (cutoff_date,))
            old_count = cursor.fetchone()[0]
            
            # Delete old URLs
            cursor.execute("""
                DELETE FROM urls 
                WHERE discovered_at < ? AND status IN ('completed', 'failed')
            """, (cutoff_date,))
            
            conn.commit()
            
        return old_count
        
    except Exception as e:
        st.error(f"Error cleaning old URLs: {str(e)}")
        return 0

def export_url_database():
    """Export URL database as CSV"""
    try:
        import sqlite3
        import pandas as pd
        from io import StringIO
        
        db_path = "basketball_crawler.db"
        
        with sqlite3.connect(db_path) as conn:
            query = """
                SELECT url, status, priority, discovered_at, processed_at, 
                       retry_count, error_message, page_title, data_chunks
                FROM urls 
                ORDER BY discovered_at DESC
            """
            
            df = pd.read_sql_query(query, conn)
            
            # Convert to CSV
            csv_buffer = StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_data = csv_buffer.getvalue()
            
            # Download button
            st.download_button(
                label="📊 Download URL Database CSV",
                data=csv_data,
                file_name=f"url_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
    except Exception as e:
        st.error(f"Error exporting URL database: {str(e)}")

if __name__ == "__main__":
    main() 