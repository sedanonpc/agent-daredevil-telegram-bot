# 🕸️ RAG Knowledge Base Visualizer

An interactive network visualization tool for your RAG (Retrieval-Augmented Generation) knowledge base using Streamlit and ECharts.

## 🌟 Features

### 📊 Interactive Network Visualization
- **Node-based Graph**: Each knowledge chunk is represented as a node
- **Relationship Mapping**: Connections show relationships between chunks
- **Color-coded Categories**: Different node colors for different content types
- **Dynamic Layout**: Force-directed graph with adjustable physics parameters
- **Interactive Controls**: Click, drag, zoom, and explore your knowledge network

### 🎨 Visual Elements
- **⚡ God Commands**: Diamond-shaped red nodes for high-priority behavior overrides
- **🏀 NBA Data**: Orange circular nodes for sports statistics
- **🌐 URL Sources**: Blue triangular nodes for web content
- **📄 File Sources**: Green rectangular nodes for uploaded documents
- **🔗 Smart Connections**: Links based on source similarity and categories

### 🛠️ Management Interface
- **Real-time Search**: Semantic search through your knowledge base
- **Content Editor**: Edit chunks directly from the graph interface
- **Advanced Filters**: Filter by type, category, word count, etc.
- **Data Explorer**: Tabular view with sorting and filtering
- **Statistics Dashboard**: Network metrics and performance insights

## 🚀 Quick Start

### Method 1: Automated Launcher (Recommended)
```bash
python launch_visualizer.py
```

The launcher will:
1. Check for required dependencies
2. Install missing packages automatically
3. Launch the Streamlit application
4. Open your browser to the visualization

### Method 2: Manual Installation
```bash
# Install dependencies
pip install -r requirements_visualizer.txt

# Launch the visualizer
streamlit run rag_knowledge_visualizer.py
```

### Method 3: Minimal Installation
```bash
# Essential packages only
pip install streamlit streamlit-echarts pyecharts networkx chromadb langchain pandas numpy

# Run the app
streamlit run rag_knowledge_visualizer.py
```

## 📋 Prerequisites

- **Python 3.8+**
- **Existing RAG Knowledge Base**: You need `rag_manager.py` and ChromaDB data
- **Internet Connection**: For initial package installation

### Required Files
Make sure these files are in the same directory:
- `rag_knowledge_visualizer.py` (the main application)
- `rag_manager.py` (your existing RAG manager)
- `chroma_db/` folder (your knowledge base data)

## 🎛️ User Interface Guide

### 🕸️ Network Graph Tab
- **Main Visualization**: Interactive force-directed graph of your knowledge
- **Node Interactions**: 
  - Click nodes to see detailed information
  - Drag nodes to rearrange the layout
  - Use mouse wheel to zoom in/out
- **Layout Controls**: Adjust physics parameters in the sidebar
  - **Repulsion**: How much nodes push away from each other
  - **Gravity**: How much nodes are attracted to the center
  - **Edge Length**: Preferred distance between connected nodes
  - **Friction**: How quickly the layout stabilizes

### 📊 Data Explorer Tab
- **Tabular View**: See all knowledge chunks in a sortable table
- **Filtering**: Multi-select filters for type, category, word count
- **Statistics**: Quick metrics about your knowledge base
- **Export Options**: View and analyze your data

### ✏️ Node Editor Tab
- **Direct Editing**: Modify chunk content, categories, and metadata
- **Rich Editor**: Full-featured text area with save/cancel options
- **Metadata Management**: Update categories, tags, and descriptions
- **Real-time Updates**: Changes reflect immediately in the graph

### 🔍 Search & Filter Tab
- **Semantic Search**: AI-powered search through your knowledge base
- **Similarity Scores**: See how relevant each result is to your query
- **Advanced Filtering**: Filter by multiple criteria simultaneously
- **Result Actions**: Edit or delete chunks directly from search results

## 🎨 Customization

### Graph Appearance
Modify these parameters in the sidebar:
- **Node Repulsion**: 500-3000 (default: 1000)
- **Gravity**: 0.1-1.0 (default: 0.2)
- **Edge Length**: 50-500 (default: 200)
- **Friction**: 0.1-1.0 (default: 0.6)

### Color Scheme
The application uses a predefined color scheme:
- 🔴 **Red (#ff4444)**: God Commands (highest priority)
- 🟠 **Orange (#ff8800)**: NBA Data
- 🔵 **Blue (#00aaff)**: URL Sources  
- 🟢 **Green (#44ff44)**: File Sources
- ⚫ **Gray (#888888)**: Other/Unknown types

## 🔧 Advanced Configuration

### Performance Optimization
For large knowledge bases (1000+ chunks):
1. Increase **Node Repulsion** to 2000-3000
2. Decrease **Gravity** to 0.1-0.15
3. Set **Friction** to 0.8-0.9 for faster stabilization
4. Use filtering to display subsets of your data

### Memory Management
- The application loads all chunks into memory for visualization
- For very large datasets, consider filtering by date ranges or categories
- Monitor browser memory usage if experiencing slowdowns

## 🐛 Troubleshooting

### Common Issues

#### "No knowledge base data found"
- **Solution**: Make sure you have documents in your ChromaDB
- **Check**: Run the regular RAG manager first to add some content

#### "ECharts component not available"
- **Solution**: Install streamlit-echarts: `pip install streamlit-echarts`
- **Alternative**: The app will fall back to a text-based representation

#### Graph not loading/empty visualization
- **Check**: Ensure `chroma_db/` folder exists and contains data
- **Verify**: Run `python -c "from rag_manager import get_collection_stats; print(get_collection_stats())"`

#### Performance issues with large graphs
- **Reduce**: Number of displayed chunks using filters
- **Adjust**: Layout parameters to stabilize faster
- **Browser**: Try using Chrome or Firefox for better WebGL performance

#### Import errors
- **Solution**: Install missing dependencies from `requirements_visualizer.txt`
- **Check**: Python version is 3.8 or higher

### Debug Mode
To run with debug information:
```bash
streamlit run rag_knowledge_visualizer.py --logger.level=debug
```

## 📈 Best Practices

### Knowledge Organization
1. **Consistent Categories**: Use standardized category names for better clustering
2. **Meaningful Tags**: Add descriptive tags to improve relationships
3. **God Commands**: Use sparingly for critical behavior modifications
4. **Regular Cleanup**: Remove outdated or duplicate chunks

### Visualization Tips
1. **Start Simple**: Begin with basic layout settings, then fine-tune
2. **Filter First**: For large datasets, filter before detailed exploration
3. **Save Configurations**: Note effective layout parameters for your data size
4. **Regular Refresh**: Reload data after making significant changes

### Performance Guidelines
- **Optimal Range**: 50-500 chunks for smooth interaction
- **Large Datasets**: Use categorical filtering to manage complexity
- **Browser Resources**: Close unnecessary tabs when working with large graphs

## 🤝 Integration with RAG Manager

The visualizer seamlessly integrates with your existing RAG Manager:
- **Shared Database**: Uses the same ChromaDB instance
- **Real-time Sync**: Changes in either tool reflect in both
- **Compatible Functions**: All RAG manager features work alongside visualization
- **Enhanced Workflow**: Visual exploration + traditional management

## 📚 Dependencies

### Core Requirements
- `streamlit>=1.28.0` - Web application framework
- `streamlit-echarts>=0.4.0` - ECharts integration for Streamlit
- `pyecharts>=1.9.1` - Python ECharts wrapper
- `networkx>=3.1` - Graph analysis library

### RAG Requirements  
- `chromadb>=0.4.15` - Vector database
- `langchain>=0.0.330` - LLM framework
- `pandas>=2.1.3` - Data manipulation
- `numpy>=1.25.2` - Numerical computing

### Optional Enhancements
- `plotly>=5.17.0` - Additional visualization options
- `matplotlib>=3.7.0` - Plotting library
- `seaborn>=0.12.0` - Statistical visualizations

## 🔜 Future Enhancements

### Planned Features
- **🔍 Semantic Clustering**: Automatic grouping of similar content
- **📊 Analytics Dashboard**: Detailed usage and performance metrics
- **🎯 Smart Recommendations**: Suggest content relationships
- **💾 Layout Persistence**: Save and restore custom graph layouts
- **🌐 Collaborative Features**: Multi-user graph exploration
- **📱 Mobile Optimization**: Responsive design for mobile devices

### Integration Roadmap
- **🤖 LLM Integration**: Direct chat interface with the knowledge graph
- **📈 Trend Analysis**: Track knowledge base evolution over time
- **🔄 Auto-Organization**: AI-powered content categorization
- **📤 Export Options**: Save graphs as images or interactive HTML

## 📄 License

This project extends the existing RAG Manager and inherits its licensing terms.

## 🙋‍♂️ Support

For issues or questions:
1. Check the troubleshooting section above
2. Ensure all dependencies are correctly installed
3. Verify your RAG Manager is working properly
4. Check that your ChromaDB contains data

---

**Happy Visualizing! 🕸️✨** 