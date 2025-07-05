import streamlit as st
import networkx as nx
from pyecharts import options as opts
from pyecharts.charts import Graph, Page
from pyecharts.globals import ThemeType
import json
import pandas as pd
import numpy as np
from datetime import datetime
import hashlib
import re
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import math
import random

# Import existing RAG manager functions
from rag_manager import (
    get_all_chunks_with_metadata,
    get_collection_stats,
    search_knowledge_base,
    delete_chunk_by_id,
    update_chunk_content,
    get_god_commands,
    init_chromadb,
    init_embeddings
)

# Import streamlit echarts for rendering
try:
    from streamlit_echarts import st_echarts
    ECHARTS_AVAILABLE = True
except ImportError:
    try:
        import streamlit.components.v1 as components
        ECHARTS_AVAILABLE = True
    except ImportError:
        ECHARTS_AVAILABLE = False

class RAGKnowledgeVisualizer:
    """RAG Knowledge Base Visualizer using Interactive Graph Networks"""
    
    def __init__(self):
        self.chunks_data = []
        self.graph_data = {"nodes": [], "links": []}
        self.network_stats = {}
        self.similarity_threshold = 0.3
        self.layout_params = {
            "repulsion": 1000,
            "gravity": 0.2,
            "edge_length": 200,
            "friction": 0.6
        }
        # Data limits to prevent memory issues
        self.max_chunks_display = 500  # Maximum chunks to display at once
        self.max_content_length = 200  # Maximum content length per chunk
        # Semantic similarity settings
        self.enable_semantic_links = True  # Enable cross-cluster semantic links
        self.max_semantic_links_per_cluster_pair = 3  # Limit semantic links to prevent clutter
    
    def load_knowledge_data(self, source_filter=None, chunk_type_filter=None, limit=None) -> bool:
        """Load knowledge base data and compute relationships with filtering"""
        try:
            # Get all chunks first
            all_chunks = get_all_chunks_with_metadata()
            if not all_chunks:
                return False
            
            # Apply filters
            filtered_chunks = all_chunks
            
            if source_filter:
                filtered_chunks = [chunk for chunk in filtered_chunks if source_filter.lower() in chunk['source'].lower()]
            
            if chunk_type_filter and chunk_type_filter != "All":
                if chunk_type_filter == "God Commands":
                    filtered_chunks = [chunk for chunk in filtered_chunks if chunk['is_god_command']]
                elif chunk_type_filter == "NBA Data":
                    filtered_chunks = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'nba_data']
                elif chunk_type_filter == "F1 Data":
                    filtered_chunks = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'f1_data']
                elif chunk_type_filter == "URL Sources":
                    filtered_chunks = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'url']
                elif chunk_type_filter == "File Sources":
                    filtered_chunks = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'file']
            
            # Apply limit (default to max_chunks_display)
            chunk_limit = limit or self.max_chunks_display
            
            # If we have too many chunks, sample them intelligently
            if len(filtered_chunks) > chunk_limit:
                # Sort by word count (descending) to prioritize larger chunks
                filtered_chunks = sorted(filtered_chunks, key=lambda x: x['word_count'], reverse=True)
                
                # Take a mix of high-quality chunks
                god_commands = [chunk for chunk in filtered_chunks if chunk['is_god_command']]
                nba_data = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'nba_data']
                f1_data = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'f1_data']
                url_sources = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'url']
                file_sources = [chunk for chunk in filtered_chunks if chunk['source_type'] == 'file']
                
                # Sample proportionally
                selected_chunks = []
                remaining_limit = chunk_limit
                
                # Always include god commands (they're important)
                god_count = min(len(god_commands), remaining_limit // 5)
                selected_chunks.extend(god_commands[:god_count])
                remaining_limit -= god_count
                
                # Add NBA data
                if remaining_limit > 0:
                    nba_count = min(len(nba_data), remaining_limit // 4)
                    selected_chunks.extend(nba_data[:nba_count])
                    remaining_limit -= nba_count
                
                # Add F1 data
                if remaining_limit > 0:
                    f1_count = min(len(f1_data), remaining_limit // 3)
                    selected_chunks.extend(f1_data[:f1_count])
                    remaining_limit -= f1_count
                
                # Add URL sources
                if remaining_limit > 0:
                    url_count = min(len(url_sources), remaining_limit // 2)
                    selected_chunks.extend(url_sources[:url_count])
                    remaining_limit -= url_count
                
                # Fill with file sources
                if remaining_limit > 0:
                    selected_chunks.extend(file_sources[:remaining_limit])
                
                filtered_chunks = selected_chunks
            
            # Optimize chunk data to reduce memory usage
            self.chunks_data = self._optimize_chunk_data(filtered_chunks)
            
            if not self.chunks_data:
                return False
            
            # Compute graph data
            self._compute_graph_data()
            self._compute_network_stats()
            return True
        except Exception as e:
            st.error(f"Error loading knowledge data: {str(e)}")
            return False

    def _optimize_chunk_data(self, chunks):
        """Optimize chunk data to reduce memory usage"""
        optimized_chunks = []
        for chunk in chunks:
            # Create a lightweight version of the chunk
            optimized_chunk = {
                'id': chunk['id'],
                'content': chunk['content'][:self.max_content_length] + "..." if len(chunk['content']) > self.max_content_length else chunk['content'],
                'source': chunk['source'],
                'source_type': chunk['source_type'],
                'category': chunk.get('category', ''),
                'tags': chunk.get('tags', ''),
                'url': chunk.get('url', ''),
                'timestamp': chunk.get('timestamp', ''),
                'word_count': chunk['word_count'],
                'is_god_command': chunk['is_god_command'],
                'priority': chunk.get('priority', 0),
                'description': chunk.get('description', ''),
                'chunk_index': chunk.get('chunk_index', 0),
                'chunk_count': chunk.get('chunk_count', 1)
            }
            optimized_chunks.append(optimized_chunk)
        return optimized_chunks

    def _compute_graph_data(self):
        """Compute nodes and links for the knowledge graph"""
        nodes = []
        links = []
        
        # Create nodes for each knowledge chunk
        for i, chunk in enumerate(self.chunks_data):
            node_id = f"chunk_{i}"
            
            # Determine node category and color
            category, color, symbol = self._get_node_style(chunk)
            
            # Calculate node size based on content length
            size = max(20, min(60, len(chunk['content']) / 50))
            
            node_name = self._create_node_label(chunk)
            
            # Create basic text tooltip with emojis only
            clean_title = node_name.replace('⚡ ', '').replace('🏀 ', '').replace('🌐 ', '').replace('📄 ', '')
            
            tooltip_text = f"📌 {clean_title}"
            
            if chunk.get('url') and chunk['url'].strip():
                url_short = chunk['url'][:40] + "..." if len(chunk['url']) > 40 else chunk['url']
                tooltip_text += f"\n🔗 {url_short}"
            
            source_short = chunk['source'][:30] + "..." if len(chunk['source']) > 30 else chunk['source']
            tooltip_text += f"\n📂 {source_short}"
            
            if chunk.get('category') and chunk['category'].strip():
                tooltip_text += f"\n📋 {chunk['category']}"
            
            if chunk.get('tags') and chunk['tags'].strip():
                tooltip_text += f"\n🏷️ {chunk['tags']}"
            
            tooltip_text += f"\n📊 {chunk['word_count']} words"
            
            if chunk['is_god_command']:
                tooltip_text += f"\n⚡ God Command"
            
            content_short = chunk['content'][:80].replace('\n', ' ').replace('\r', ' ')
            content_short = re.sub(r'\s+', ' ', content_short).strip()
            if len(chunk['content']) > 80:
                content_short += "..."
            tooltip_text += f"\n📝 {content_short}"
            
            detailed_name = tooltip_text
            
            node = {
                "id": node_id,
                "name": detailed_name,  # Use the detailed info as the name
                "category": category,
                "symbolSize": size,
                "value": chunk['word_count'],
                "itemStyle": {"color": color},
                "symbol": symbol,
                "label": {
                    "show": True,
                    "fontSize": 10,
                    "formatter": node_name  # Show clean name on the graph
                },
                # Store chunk data for interactions
                "chunk_data": {
                    "chunk_id": chunk['id'],
                    "source": chunk['source'],
                    "category": chunk['category'],
                    "tags": chunk.get('tags', ''),
                    "content": chunk['content'][:self.max_content_length] + "..." if len(chunk['content']) > self.max_content_length else chunk['content'],
                    "content_preview": chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content'],
                    "word_count": chunk['word_count'],
                    "is_god_command": chunk['is_god_command'],
                    "timestamp": chunk['timestamp'],
                    "url": chunk.get('url', ''),
                    "source_type": chunk['source_type']
                }
            }
            nodes.append(node)
        
        # Create links based on relationships
        links = self._compute_relationships()
        
        self.graph_data = {
            "nodes": nodes,
            "links": links,
            "categories": self._get_categories()
        }
    
    def _get_node_style(self, chunk) -> Tuple[str, str, str]:
        """Get node styling based on chunk type"""
        if chunk['is_god_command']:
            return "God Commands", "#ff4444", "diamond"
        elif chunk['source_type'] == 'nba_data':
            return "NBA Data", "#ff8800", "circle"
        elif chunk['source_type'] == 'f1_data':
            return "F1 Data", "#dc143c", "rect"  # Ferrari red
        elif chunk['source_type'] == 'url':
            return "URL Sources", "#00aaff", "triangle"
        elif chunk['source_type'] == 'file':
            return "File Sources", "#44ff44", "rect"
        else:
            return "Other", "#888888", "circle"
    
    def _create_node_label(self, chunk) -> str:
        """Create a readable label for the node using tags/categories"""
        # Priority: tags > category > source type
        label_text = ""
        
        # First try to use tags
        if chunk.get('tags') and chunk['tags'].strip():
            # Use the first tag if multiple tags exist
            first_tag = chunk['tags'].split(',')[0].strip()
            label_text = first_tag[:25] + "..." if len(first_tag) > 25 else first_tag
        # Then try category
        elif chunk.get('category') and chunk['category'].strip():
            category = chunk['category']
            label_text = category[:25] + "..." if len(category) > 25 else category
        # Fallback to content preview
        else:
            content_preview = chunk['content'][:20].replace('\n', ' ').strip()
            label_text = content_preview + "..." if len(chunk['content']) > 20 else content_preview
        
        # Add emoji prefix based on type
        if chunk['is_god_command']:
            return f"⚡ {label_text}"
        elif chunk['source_type'] == 'nba_data':
            return f"🏀 {label_text}"
        elif chunk['source_type'] == 'f1_data':
            return f"🏎️ {label_text}"
        elif chunk['source_type'] == 'url':
            return f"🌐 {label_text}"
        else:
            return f"📄 {label_text}"
    

    
    def _compute_relationships(self) -> List[Dict]:
        """Compute relationships between knowledge chunks"""
        links = []
        
        # Group chunks by source
        source_groups = defaultdict(list)
        for i, chunk in enumerate(self.chunks_data):
            source_groups[chunk['source']].append(i)
        
        # Create links within the same source
        for source, chunk_indices in source_groups.items():
            if len(chunk_indices) > 1:
                for i in range(len(chunk_indices)):
                    for j in range(i + 1, len(chunk_indices)):
                        links.append({
                            "source": f"chunk_{chunk_indices[i]}",
                            "target": f"chunk_{chunk_indices[j]}",
                            "value": 1,
                            "lineStyle": {"color": "#cccccc", "width": 1},
                            "label": {"show": False}
                        })
        
        # Create links based on category similarity
        category_groups = defaultdict(list)
        for i, chunk in enumerate(self.chunks_data):
            if chunk['category']:
                category_groups[chunk['category']].append(i)
        
        for category, chunk_indices in category_groups.items():
            if len(chunk_indices) > 1:
                # Create weaker links for category relationships
                for i in range(len(chunk_indices)):
                    for j in range(i + 1, min(i + 3, len(chunk_indices))):  # Limit to prevent too many links
                        if f"chunk_{chunk_indices[i]}" != f"chunk_{chunk_indices[j]}":
                            # Check if link already exists
                            existing = any(
                                (link["source"] == f"chunk_{chunk_indices[i]}" and link["target"] == f"chunk_{chunk_indices[j]}") or
                                (link["source"] == f"chunk_{chunk_indices[j]}" and link["target"] == f"chunk_{chunk_indices[i]}")
                                for link in links
                            )
                            if not existing:
                                links.append({
                                    "source": f"chunk_{chunk_indices[i]}",
                                    "target": f"chunk_{chunk_indices[j]}",
                                    "value": 0.5,
                                    "lineStyle": {"color": "#e0e0e0", "width": 1, "type": "dashed"},
                                    "label": {"show": False}
                                })
        
        # NEW: Create semantic similarity links between different clusters (NEON GREEN)
        if self.enable_semantic_links:
            semantic_links = self._compute_semantic_cross_cluster_links()
            links.extend(semantic_links)
        
        # Create special links for God Commands (they should be prominent)
        god_command_indices = [i for i, chunk in enumerate(self.chunks_data) if chunk['is_god_command']]
        for god_idx in god_command_indices:
            # Connect god commands to a few related chunks
            for i, chunk in enumerate(self.chunks_data[:5]):  # Connect to first 5 chunks as example
                if i != god_idx:
                    links.append({
                        "source": f"chunk_{god_idx}",
                        "target": f"chunk_{i}",
                        "value": 2,
                        "lineStyle": {"color": "#ff6666", "width": 2},
                        "label": {"show": False}
                    })
        
        return links
    
    def _compute_semantic_cross_cluster_links(self) -> List[Dict]:
        """Compute semantic similarity links between different source clusters"""
        semantic_links = []
        
        # Group chunks by source
        source_groups = defaultdict(list)
        for i, chunk in enumerate(self.chunks_data):
            source_groups[chunk['source']].append((i, chunk))
        
        # Get all source pairs for cross-cluster comparison
        source_list = list(source_groups.keys())
        
        # For each pair of different sources, find semantic similarities
        for i in range(len(source_list)):
            for j in range(i + 1, len(source_list)):
                source1, source2 = source_list[i], source_list[j]
                
                # Get chunks from both sources
                chunks1 = source_groups[source1]
                chunks2 = source_groups[source2]
                
                # Find semantic connections between these sources
                cross_connections = self._find_semantic_matches(chunks1, chunks2)
                
                # Add neon green links for semantic connections
                for conn in cross_connections:
                    semantic_links.append({
                        "source": f"chunk_{conn['source_idx']}",
                        "target": f"chunk_{conn['target_idx']}",
                        "value": conn['similarity'],
                        "lineStyle": {
                            "color": "#00ff41",  # Neon green
                            "width": 2,
                            "type": "solid",
                            "shadowColor": "#00ff41",
                            "shadowBlur": 5
                        },
                        "label": {"show": False}
                    })
        
        return semantic_links
    
    def _find_semantic_matches(self, chunks1, chunks2) -> List[Dict]:
        """Find semantic matches between two groups of chunks"""
        matches = []
        
        # Limit the number of connections to prevent visual clutter
        max_connections_per_source_pair = self.max_semantic_links_per_cluster_pair
        
        for idx1, chunk1 in chunks1[:10]:  # Limit to first 10 chunks per source
            for idx2, chunk2 in chunks2[:10]:
                similarity = self._calculate_semantic_similarity(chunk1, chunk2)
                
                # Only create connections above a threshold
                if similarity > 0.3:  # Adjust threshold as needed
                    matches.append({
                        'source_idx': idx1,
                        'target_idx': idx2,
                        'similarity': similarity
                    })
        
        # Sort by similarity and take top connections
        matches.sort(key=lambda x: x['similarity'], reverse=True)
        return matches[:max_connections_per_source_pair]
    
    def _calculate_semantic_similarity(self, chunk1, chunk2) -> float:
        """Calculate semantic similarity between two chunks"""
        # Extract text content for comparison
        text1 = f"{chunk1.get('tags', '')} {chunk1.get('category', '')} {chunk1['content'][:100]}".lower()
        text2 = f"{chunk2.get('tags', '')} {chunk2.get('category', '')} {chunk2['content'][:100]}".lower()
        
        # Simple keyword-based similarity
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those'}
        
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate Jaccard similarity
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # Boost similarity for chunks with same category or tags
        category_bonus = 0.2 if chunk1.get('category') and chunk1.get('category') == chunk2.get('category') else 0.0
        tags_bonus = 0.2 if chunk1.get('tags') and chunk2.get('tags') and any(tag.strip() in chunk2.get('tags', '') for tag in chunk1.get('tags', '').split(',')) else 0.0
        
        # Boost similarity for god commands
        god_bonus = 0.3 if chunk1.get('is_god_command') or chunk2.get('is_god_command') else 0.0
        
        total_similarity = min(1.0, jaccard_similarity + category_bonus + tags_bonus + god_bonus)
        
        return total_similarity
    
    def _get_categories(self) -> List[Dict]:
        """Get category definitions for the legend"""
        return [
            {"name": "God Commands", "itemStyle": {"color": "#ff4444"}},
            {"name": "NBA Data", "itemStyle": {"color": "#ff8800"}},
            {"name": "F1 Data", "itemStyle": {"color": "#dc143c"}},  # Ferrari red
            {"name": "URL Sources", "itemStyle": {"color": "#00aaff"}},
            {"name": "File Sources", "itemStyle": {"color": "#44ff44"}},
            {"name": "Other", "itemStyle": {"color": "#888888"}}
        ]
    
    def _compute_network_stats(self):
        """Compute network statistics"""
        # Count semantic links (neon green ones)
        semantic_links_count = len([link for link in self.graph_data["links"] if link["lineStyle"]["color"] == "#00ff41"]) if self.graph_data["links"] else 0
        
        self.network_stats = {
            "total_nodes": len(self.graph_data["nodes"]),
            "total_links": len(self.graph_data["links"]),
            "semantic_links": semantic_links_count,
            "god_commands": len([n for n in self.graph_data["nodes"] if "⚡" in n["name"]]),
            "nba_data": len([n for n in self.graph_data["nodes"] if "🏀" in n["name"]]),
            "f1_data": len([n for n in self.graph_data["nodes"] if "🏎️" in n["name"]]),
            "url_sources": len([n for n in self.graph_data["nodes"] if "🌐" in n["name"]]),
            "file_sources": len([n for n in self.graph_data["nodes"] if "📄" in n["name"]]),
            "avg_connections": len(self.graph_data["links"]) / len(self.graph_data["nodes"]) if self.graph_data["nodes"] else 0
        }
    
    def create_echarts_graph(self) -> Dict:
        """Create ECharts graph configuration"""
        option = {
            "title": {
                "text": "RAG Knowledge Base Network",
                "subtext": f"{self.network_stats['total_nodes']} chunks, {self.network_stats['total_links']} connections ({self.network_stats.get('semantic_links', 0)} semantic)",
                "top": 10,
                "left": 10
            },
            "tooltip": {
                "show": True,
                "trigger": "item",
                "textStyle": {
                    "fontSize": 12
                },
                "extraCssText": "white-space: pre-line; max-width: 350px;"
            },
            "legend": {
                "data": [cat["name"] for cat in self.graph_data["categories"]],
                "top": 10,
                "right": 10,
                "orient": "vertical"
            },
            "animationDuration": 1500,
            "animationEasingUpdate": "quinticInOut",
            "series": [{
                "name": "Knowledge Network",
                "type": "graph",
                "layout": "force",
                "data": self.graph_data["nodes"],
                "links": self.graph_data["links"],
                "categories": self.graph_data["categories"],
                "roam": True,
                "focusNodeAdjacency": True,
                "itemStyle": {
                    "borderColor": "#fff",
                    "borderWidth": 1,
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0, 0, 0, 0.3)"
                },
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{b}"
                },
                "lineStyle": {
                    "color": "source",
                    "curveness": 0.3
                },
                "emphasis": {
                    "focus": "adjacency",
                    "lineStyle": {
                        "width": 3
                    }
                },
                "force": {
                    "repulsion": self.layout_params["repulsion"],
                    "gravity": self.layout_params["gravity"],
                    "edgeLength": self.layout_params["edge_length"],
                    "friction": self.layout_params["friction"],
                    "layoutAnimation": True
                }
            }]
        }
        
        return option

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="RAG Knowledge Visualizer",
        page_icon="🕸️",
        layout="wide"
    )
    
    st.title("🕸️ RAG Knowledge Base Visualizer")
    st.markdown("**Interactive network visualization of your RAG knowledge base**")
    
    # Memory optimization info
    st.info("""
    📚 **Memory Optimization Enabled**: For large knowledge bases, this visualizer automatically limits the number of chunks displayed 
    and truncates content to prevent browser memory issues. Use the filters in the sidebar to focus on specific data.
    """)
    
    # New feature announcement
    st.success("""
    🌟 **NEW: Cross-Cluster Semantic Links** - Neon green lines now show semantic relationships between different knowledge clusters!
    """)
    
    # Initialize session state
    if 'visualizer' not in st.session_state:
        st.session_state.visualizer = RAGKnowledgeVisualizer()
    
    if 'selected_node' not in st.session_state:
        st.session_state.selected_node = None
    
    if 'graph_needs_refresh' not in st.session_state:
        st.session_state.graph_needs_refresh = True
    
    visualizer = st.session_state.visualizer
    
    # Sidebar controls
    with st.sidebar:
        st.header("🎛️ Graph Controls")
        
        # Semantic links control
        st.subheader("🔗 Semantic Links")
        
        enable_semantic = st.checkbox(
            "Enable Cross-Cluster Semantic Links",
            value=visualizer.enable_semantic_links,
            help="Show neon green lines connecting semantically similar chunks from different clusters"
        )
        
        if enable_semantic != visualizer.enable_semantic_links:
            visualizer.enable_semantic_links = enable_semantic
            st.session_state.graph_needs_refresh = True
        
        max_semantic_links = st.slider(
            "Max Semantic Links per Cluster Pair:",
            min_value=1,
            max_value=10,
            value=visualizer.max_semantic_links_per_cluster_pair,
            help="Limit semantic links to prevent visual clutter"
        )
        
        if max_semantic_links != visualizer.max_semantic_links_per_cluster_pair:
            visualizer.max_semantic_links_per_cluster_pair = max_semantic_links
            st.session_state.graph_needs_refresh = True
        
        # Data filtering controls
        st.subheader("🔍 Data Filters")
        
        # Chunk limit
        chunk_limit = st.slider(
            "Max Chunks to Display:",
            min_value=50,
            max_value=1000,
            value=visualizer.max_chunks_display,
            step=50,
            help="Limit the number of chunks to prevent memory issues"
        )
        
        # Source filter
        source_filter = st.text_input(
            "Filter by Source:",
            value="",
            help="Enter text to filter chunks by source name"
        )
        
        # Chunk type filter
        chunk_type_filter = st.selectbox(
            "Filter by Type:",
            ["All", "God Commands", "NBA Data", "F1 Data", "URL Sources", "File Sources"],
            help="Filter chunks by their type"
        )
        
        # Apply filters button
        if st.button("🔍 Apply Filters"):
            st.session_state.graph_needs_refresh = True
        
        # Refresh data button
        if st.button("🔄 Refresh Data", help="Reload knowledge base data"):
            st.session_state.graph_needs_refresh = True
        
        # Layout parameters
        st.subheader("📐 Layout Settings")
        
        new_repulsion = st.slider(
            "Node Repulsion:",
            min_value=500,
            max_value=3000,
            value=visualizer.layout_params["repulsion"],
            step=100,
            help="How much nodes repel each other"
        )
        
        new_gravity = st.slider(
            "Gravity:",
            min_value=0.1,
            max_value=1.0,
            value=visualizer.layout_params["gravity"],
            step=0.1,
            help="How much nodes are attracted to center"
        )
        
        new_edge_length = st.slider(
            "Edge Length:",
            min_value=50,
            max_value=500,
            value=visualizer.layout_params["edge_length"],
            step=25,
            help="Preferred distance between connected nodes"
        )
        
        new_friction = st.slider(
            "Friction:",
            min_value=0.1,
            max_value=1.0,
            value=visualizer.layout_params["friction"],
            step=0.1,
            help="How quickly the layout stabilizes"
        )
        
        # Update layout if changed
        if (new_repulsion != visualizer.layout_params["repulsion"] or
            new_gravity != visualizer.layout_params["gravity"] or
            new_edge_length != visualizer.layout_params["edge_length"] or
            new_friction != visualizer.layout_params["friction"]):
            
            visualizer.layout_params.update({
                "repulsion": new_repulsion,
                "gravity": new_gravity,
                "edge_length": new_edge_length,
                "friction": new_friction
            })
            st.session_state.graph_needs_refresh = True
        
        # Graph statistics
        if hasattr(visualizer, 'network_stats') and visualizer.network_stats:
            st.subheader("📊 Network Statistics")
            stats = visualizer.network_stats
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Nodes", stats['total_nodes'])
                st.metric("God Commands", stats['god_commands'])
                st.metric("NBA Data", stats['nba_data'])
                st.metric("F1 Data", stats.get('f1_data', 0))
            
            with col2:
                st.metric("Total Links", stats['total_links'])
                st.metric("Semantic Links", stats.get('semantic_links', 0))
                st.metric("URL Sources", stats['url_sources'])
                st.metric("File Sources", stats['file_sources'])
            
            st.metric("Avg Connections", f"{stats['avg_connections']:.1f}")
            
            # Connection types legend
            st.subheader("🎨 Connection Types")
            st.markdown("""
            - **Gray**: Same source document
            - **Light Gray Dashed**: Same category/tags
            - **🟢 Neon Green**: Semantic similarity (cross-cluster)
            - **Red**: God command connections
            """)
    
    # Load data if needed
    if st.session_state.graph_needs_refresh:
        with st.spinner("Loading knowledge base data..."):
            # Apply filters
            filter_source = source_filter.strip() if source_filter.strip() else None
            filter_type = chunk_type_filter if chunk_type_filter != "All" else None
            
            success = visualizer.load_knowledge_data(
                source_filter=filter_source,
                chunk_type_filter=filter_type,
                limit=chunk_limit
            )
            if not success:
                st.error("No knowledge base data found. Please add some documents first using the RAG Manager.")
                st.stop()
            st.session_state.graph_needs_refresh = False
            
            # Show data loading summary
            st.success(f"✅ Loaded {len(visualizer.chunks_data)} chunks for visualization")
            if visualizer.enable_semantic_links:
                semantic_count = visualizer.network_stats.get('semantic_links', 0)
                st.info(f"🔗 Created {semantic_count} semantic cross-cluster connections")
            if filter_source or filter_type:
                st.info(f"🔍 Applied filters: Source='{filter_source}', Type='{filter_type}'")
    
    # Main content area
    if not visualizer.chunks_data:
        st.warning("⚠️ No knowledge base data loaded. Please refresh or add some documents.")
        return
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "🕸️ Network Graph", 
        "📊 Data Explorer", 
        "✏️ Node Editor",
        "🔍 Search & Filter"
    ])
    
    with tab1:
        st.subheader("🕸️ Interactive Knowledge Network")
        st.markdown("**Click on nodes to see details, drag to rearrange the network**")
        
        # Create ECharts graph if available
        if ECHARTS_AVAILABLE:
            option = visualizer.create_echarts_graph()
            
            # Add click events to capture node selections
            events = {
                "click": """
                function(params) {
                    if (params.dataType === 'node') {
                        console.log('Node clicked:', params.data);
                        return {
                            'node_id': params.data.id,
                            'chunk_id': params.data.chunk_data.chunk_id,
                            'source': params.data.chunk_data.source,
                            'event': 'node_click'
                        };
                    }
                }
                """
            }
            
            # Render the graph
            graph_events = st_echarts(
                options=option,
                events=events,
                height="800px",
                key="knowledge_graph"
            )
            
            # Handle node click events
            if graph_events and graph_events.get('event') == 'node_click':
                st.session_state.selected_node = graph_events
                st.rerun()
            
        else:
            st.error("ECharts component not available. Please install streamlit-echarts: pip install streamlit-echarts")
            
            # Show basic graph info instead
            st.info(f"Graph would show {len(visualizer.chunks_data)} nodes with relationships")
            for i, chunk in enumerate(visualizer.chunks_data[:10]):  # Show first 10 as example
                st.write(f"- {chunk['source']} ({chunk['word_count']} words)")
        
        # Show selected node info
        if st.session_state.selected_node:
            st.subheader("🎯 Selected Node Details")
            node_info = st.session_state.selected_node
            
            # Find the full chunk data
            chunk_data = None
            for chunk in visualizer.chunks_data:
                if chunk['id'] == node_info['chunk_id']:
                    chunk_data = chunk
                    break
            
            if chunk_data:
                # Create the title from tags/category
                title = ""
                if chunk_data.get('tags') and chunk_data['tags'].strip():
                    title = chunk_data['tags'].split(',')[0].strip()
                elif chunk_data.get('category') and chunk_data['category'].strip():
                    title = chunk_data['category']
                else:
                    title = chunk_data['content'][:30].replace('\n', ' ').strip() + "..."
                
                # Display title prominently with better styling
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                           color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: white;">📌 {title}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # URL Source (if available) - Enhanced display
                if chunk_data.get('url') and chunk_data['url'].strip():
                    st.markdown(f"""
                    <div style="background: #e8f5e8; padding: 10px; border-radius: 8px; 
                               border-left: 4px solid #28a745; margin-bottom: 15px;">
                        <strong style="color: #155724;">🔗 Source URL:</strong><br>
                        <a href="{chunk_data['url']}" target="_blank" style="color: #007bff; 
                           text-decoration: none; word-break: break-all;">{chunk_data['url']}</a>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Metadata cards
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"""
                    <div style="background: #f8f9fa; padding: 12px; border-radius: 8px; margin-bottom: 10px;">
                        <strong>📂 Source File:</strong><br>
                        <span style="color: #495057; font-size: 14px;">{chunk_data['source']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if chunk_data.get('category') and chunk_data['category'].strip():
                        st.markdown(f"""
                        <div style="background: #e3f2fd; padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                            <strong style="color: #1976d2;">📋 Category:</strong> {chunk_data['category']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                    if chunk_data.get('tags') and chunk_data['tags'].strip():
                        st.markdown(f"""
                        <div style="background: #f3e5f5; padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                            <strong style="color: #7b1fa2;">🏷️ Tags:</strong> {chunk_data['tags']}
                        </div>
                        """, unsafe_allow_html=True)
                    
                with col2:
                    st.markdown(f"""
                    <div style="background: #fff3cd; padding: 10px; border-radius: 8px; margin-bottom: 10px;">
                        <strong style="color: #856404;">📊 Word Count:</strong><br>
                        <span style="font-size: 18px; font-weight: bold; color: #856404;">{chunk_data['word_count']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="background: #d1ecf1; padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                        <strong style="color: #0c5460;">📁 Type:</strong> {chunk_data['source_type']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if chunk_data['is_god_command']:
                        st.markdown(f"""
                        <div style="background: #f8d7da; padding: 8px; border-radius: 6px; margin-bottom: 8px;">
                            <strong style="color: #721c24;">⚡ God Command</strong>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Text Content (Emphasized with better styling)
                st.markdown("""
                <div style="background: #2c3e50; color: white; padding: 12px; border-radius: 8px 8px 0 0; margin-top: 20px;">
                    <h3 style="margin: 0; color: white;">📝 Complete Content</h3>
                </div>
                """, unsafe_allow_html=True)
                
                # Content display with proper text wrapping and formatting
                st.text_area(
                    "",
                    value=chunk_data['content'],
                    height=300,
                    disabled=True,
                    key="selected_node_content",
                    help="Complete text content of the selected knowledge chunk"
                )
            
            with col2:
                if st.button("✏️ Edit This Chunk", type="primary"):
                    st.session_state.edit_chunk_id = node_info['chunk_id']
                    # Note: In a real app, you'd switch to the editor tab
                
                if st.button("🗑️ Delete This Chunk", type="secondary"):
                    if st.checkbox("Confirm deletion", key="confirm_delete"):
                        success, message = delete_chunk_by_id(node_info['chunk_id'])
                        if success:
                            st.success("Chunk deleted successfully!")
                            st.session_state.graph_needs_refresh = True
                            st.session_state.selected_node = None
                            st.rerun()
                        else:
                            st.error(f"Error deleting chunk: {message}")
    
    with tab2:
        st.subheader("📊 Knowledge Base Data Explorer")
        
        if visualizer.chunks_data:
            # Create DataFrame for better exploration
            df_data = []
            for chunk in visualizer.chunks_data:
                df_data.append({
                    "Source": chunk['source'],
                    "Category": chunk['category'],
                    "Type": "God Command" if chunk['is_god_command'] else chunk['source_type'].title(),
                    "Word Count": chunk['word_count'],
                    "Character Count": chunk['char_count'],
                    "Timestamp": chunk['timestamp'][:16] if chunk['timestamp'] else "Unknown",
                    "Content Preview": chunk['content'][:100] + "..." if len(chunk['content']) > 100 else chunk['content']
                })
            
            df = pd.DataFrame(df_data)
            
            # Add filters
            col1, col2, col3 = st.columns(3)
            
            with col1:
                type_filter = st.multiselect(
                    "Filter by Type:",
                    options=df["Type"].unique(),
                    default=df["Type"].unique()
                )
            
            with col2:
                category_filter = st.multiselect(
                    "Filter by Category:",
                    options=df["Category"].unique(),
                    default=df["Category"].unique()
                )
            
            with col3:
                word_count_range = st.slider(
                    "Word Count Range:",
                    min_value=int(df["Word Count"].min()),
                    max_value=int(df["Word Count"].max()),
                    value=(int(df["Word Count"].min()), int(df["Word Count"].max()))
                )
            
            # Apply filters
            filtered_df = df[
                (df["Type"].isin(type_filter)) &
                (df["Category"].isin(category_filter)) &
                (df["Word Count"] >= word_count_range[0]) &
                (df["Word Count"] <= word_count_range[1])
            ]
            
            st.write(f"**Showing {len(filtered_df)} of {len(df)} chunks**")
            
            st.dataframe(
                filtered_df,
                use_container_width=True,
                hide_index=True
            )
            
            # Quick stats
            st.subheader("📈 Quick Statistics")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Chunks", len(filtered_df))
            
            with col2:
                st.metric("Avg Word Count", f"{filtered_df['Word Count'].mean():.1f}")
            
            with col3:
                st.metric("Categories", filtered_df["Category"].nunique())
            
            with col4:
                st.metric("Sources", filtered_df["Source"].nunique())
    
    with tab3:
        st.subheader("✏️ Knowledge Chunk Editor")
        
        # Check if we have a chunk to edit from node selection
        edit_chunk_id = st.session_state.get('edit_chunk_id', None)
        
        if edit_chunk_id:
            # Find the chunk to edit
            chunk_to_edit = None
            for chunk in visualizer.chunks_data:
                if chunk['id'] == edit_chunk_id:
                    chunk_to_edit = chunk
                    break
            
            if chunk_to_edit:
                st.info(f"**Editing chunk from:** {chunk_to_edit['source']}")
                
                # Edit form
                with st.form("edit_chunk_form"):
                    new_content = st.text_area(
                        "Content:",
                        value=chunk_to_edit['content'],
                        height=300
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        new_category = st.text_input(
                            "Category:",
                            value=chunk_to_edit['category']
                        )
                    
                    with col2:
                        new_tags = st.text_input(
                            "Tags:",
                            value=chunk_to_edit.get('tags', '')
                        )
                    
                    new_description = st.text_area(
                        "Description:",
                        value=chunk_to_edit.get('description', ''),
                        height=100
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        save_changes = st.form_submit_button("💾 Save Changes", type="primary")
                    
                    with col2:
                        cancel_edit = st.form_submit_button("❌ Cancel")
                
                if save_changes:
                    # Update the chunk
                    updated_metadata = {
                        'category': new_category,
                        'tags': new_tags,
                        'description': new_description
                    }
                    
                    success, message = update_chunk_content(
                        edit_chunk_id,
                        new_content,
                        updated_metadata
                    )
                    
                    if success:
                        st.success("✅ Chunk updated successfully!")
                        st.session_state.graph_needs_refresh = True
                        st.session_state.edit_chunk_id = None
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"❌ Error updating chunk: {message}")
                
                if cancel_edit:
                    st.session_state.edit_chunk_id = None
                    st.rerun()
            
            else:
                st.error("Chunk not found for editing.")
                st.session_state.edit_chunk_id = None
        
        else:
            # Manual chunk selection for editing
            st.info("Select a chunk to edit from the dropdown or click on a node in the network graph.")
            
            if visualizer.chunks_data:
                # Create a dropdown for manual selection
                chunk_options = {}
                for chunk in visualizer.chunks_data:
                    label = f"{chunk['source'][:50]}... ({chunk['word_count']} words)"
                    chunk_options[label] = chunk['id']
                
                selected_label = st.selectbox(
                    "Choose a chunk to edit:",
                    [""] + list(chunk_options.keys())
                )
                
                if selected_label:
                    st.session_state.edit_chunk_id = chunk_options[selected_label]
                    st.rerun()
    
    with tab4:
        st.subheader("🔍 Search & Filter Knowledge")
        
        # Search functionality
        search_query = st.text_input(
            "🔍 Search in knowledge base:",
            placeholder="Enter your search query..."
        )
        
        col1, col2 = st.columns(2)
        with col1:
            search_k = st.slider("Number of results:", 1, 20, 5)
        
        with col2:
            show_similarity_scores = st.checkbox("Show similarity scores", value=True)
        
        if search_query and st.button("🔍 Search", type="primary"):
            with st.spinner("Searching knowledge base..."):
                try:
                    results = search_knowledge_base(search_query, search_k)
                    
                    if results:
                        st.subheader(f"📋 Found {len(results)} results")
                        
                        for i, (doc, score) in enumerate(results, 1):
                            with st.expander(
                                f"Result {i} - {doc.metadata.get('source', 'Unknown')} "
                                f"{f'(Score: {score:.4f})' if show_similarity_scores else ''}"
                            ):
                                st.write("**Content:**")
                                st.write(doc.page_content)
                                
                                st.write("**Metadata:**")
                                metadata_cols = st.columns(2)
                                
                                with metadata_cols[0]:
                                    st.write(f"**Source:** {doc.metadata.get('source', 'Unknown')}")
                                    st.write(f"**Category:** {doc.metadata.get('category', 'Uncategorized')}")
                                    st.write(f"**Type:** {doc.metadata.get('source_type', 'unknown')}")
                                
                                with metadata_cols[1]:
                                    st.write(f"**Timestamp:** {doc.metadata.get('timestamp', 'Unknown')}")
                                    if doc.metadata.get('url'):
                                        st.write(f"**URL:** {doc.metadata['url']}")
                                    if doc.metadata.get('is_god_command'):
                                        st.write("**⚡ God Command**")
                    else:
                        st.warning("No results found. Try a different search query.")
                
                except Exception as e:
                    st.error(f"Search error: {str(e)}")

if __name__ == "__main__":
    main() 