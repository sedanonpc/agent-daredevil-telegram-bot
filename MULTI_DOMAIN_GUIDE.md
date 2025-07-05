# 🌐 Multi-Domain RAG System Guide

Agent Daredevil now supports **compartmentalized reasoning** between NBA Basketball and Formula 1 Racing domains! This guide explains how to use the new multi-domain capabilities.

## 🚀 Quick Start

### 1. Enable Multi-Domain Mode

The multi-domain system is enabled by default. To toggle it:

```bash
# Enable (default)
export USE_MULTI_DOMAIN=True

# Disable (fall back to standard RAG)
export USE_MULTI_DOMAIN=False
```

### 2. Test the System

Run the test script to see domain detection in action:

```bash
python test_multi_domain_rag.py
```

This will:
- Test domain detection on various queries
- Add sample domain-specific God Commands
- Demonstrate compartmentalized responses

### 3. Start Agent Daredevil

```bash
python launch_daredevil.py
```

The system will show domain distribution in the startup logs:
```
[+] Multi-Domain RAG system initialized successfully!
[+] Domain distribution: {'nba': 15, 'f1': 8, 'general': 23}
```

## 🏀🏎️ Domain Features

### Domain Detection

The system automatically detects domain based on keywords:

| Query | Detected Domain | Response Style |
|-------|----------------|----------------|
| "How did the Lakers perform?" | 🏀 NBA Basketball | Expert basketball analyst |
| "What's Ferrari's strategy?" | 🏎️ Formula 1 Racing | Expert racing analyst |
| "Compare LeBron and Hamilton" | 🔄 Multi-domain | Cross-sport insights |
| "What's the weather?" | ❌ General | Standard Agent Daredevil |

### Response Indicators

New emoji indicators show domain detection:

- **⚡🏀** = NBA God Commands active
- **⚡🏎️** = F1 God Commands active  
- **🏀** = NBA domain detected
- **🏎️** = F1 domain detected
- **🔄** = Multi-domain query
- **⚡** = General God Commands

### Domain-Specific Knowledge

Each domain maintains separate knowledge:

**🏀 NBA Domain (`nba_data`)**
- Player statistics and performance
- Team standings and playoff positions
- Game results and schedules
- Trade news and injury reports

**🏎️ F1 Domain (`f1_data`)**
- Driver and constructor standings
- Race results and qualifying times
- Technical regulations and car development
- Strategy analysis and pit stops

## ⚡ Domain-Specific God Commands

### NBA Analyst Commands

```bash
# Example NBA God Commands (automatically added by test script)
NBA_ANALYST_01: When discussing NBA topics, respond as an expert basketball analyst...
NBA_ANALYST_02: For NBA queries, prioritize current season data and statistics...
NBA_ANALYST_03: When discussing teams, consider playoff position and strategy...
```

### F1 Racing Commands

```bash
# Example F1 God Commands (automatically added by test script)  
F1_ANALYST_01: When discussing Formula 1, respond as a knowledgeable racing expert...
F1_ANALYST_02: For F1 queries, prioritize qualifying results and race performance...
F1_ANALYST_03: When discussing constructors, consider championship position and technical analysis...
```

## 🛠️ Adding Domain Data

### NBA Data

Use source type `nba_data` when adding NBA content:

```python
from rag_manager import add_to_knowledge_base

# Add NBA data
success, chunks = add_to_knowledge_base(
    text="Lakers beat Warriors 112-108...",
    filename="nba_game_2024_01_15",
    metadata={
        "source_type": "nba_data",
        "category": "game_results",
        "tags": "Lakers, Warriors, January 2024"
    }
)
```

### F1 Data

Use source type `f1_data` when adding F1 content:

```python
from rag_manager import add_to_knowledge_base

# Add F1 data
success, chunks = add_to_knowledge_base(
    text="Ferrari introduces new aerodynamic package...",
    filename="f1_technical_2024_monaco",
    metadata={
        "source_type": "f1_data", 
        "category": "technical_updates",
        "tags": "Ferrari, aerodynamics, Monaco 2024"
    }
)
```

## 📊 Visualizer Enhancements

The Knowledge Visualizer now supports F1 data:

### New Features

- **🏎️ F1 Data Nodes**: Ferrari red color scheme
- **Filter Options**: Separate F1 data filtering
- **Domain Statistics**: Shows NBA vs F1 data distribution
- **Semantic Links**: Cross-cluster connections between domains

### Access the Visualizer

```bash
# Via launcher (recommended)
python launch_daredevil.py

# Direct access
streamlit run rag_knowledge_visualizer.py --server.port 8502
```

Navigate to: http://localhost:8502

## 🔧 Advanced Configuration

### Domain Keywords

Customize domain detection by modifying `multi_domain_rag.py`:

```python
# Add more NBA keywords
'nba': DomainConfig(
    keywords=[
        'nba', 'basketball', 'lakers', 'warriors', # existing
        'nets', 'clippers', 'mavs'  # add more teams
    ]
)

# Add more F1 keywords  
'f1': DomainConfig(
    keywords=[
        'f1', 'formula1', 'ferrari', 'mercedes', # existing
        'drs', 'kers', 'bahrain', 'silverstone'  # add more terms
    ]
)
```

### Priority Boost

Adjust domain priority in search results:

```python
'nba': DomainConfig(
    priority_boost=1.5  # Higher boost = higher priority
)
```

### Source Types

Map content to domains using source types:

- `nba_data` → NBA Basketball domain
- `f1_data` → Formula 1 Racing domain
- `url` → General web content
- `file` → General file content
- `god_command` → Behavior overrides

## 🎯 Example Interactions

### Single Domain Queries

```
User: "How did LeBron play last night?"

Agent: 🏀 *NBA domain detected*
As an expert basketball analyst, I can tell you that LeBron...
[Uses NBA-specific knowledge and terminology]
```

```
User: "What's Max Verstappen's championship position?"

Agent: 🏎️ *F1 domain detected*  
As a knowledgeable F1 racing expert, Verstappen currently leads...
[Uses F1-specific knowledge and racing terminology]
```

### Multi-Domain Queries

```
User: "Compare Michael Jordan and Ayrton Senna as legends"

Agent: 🔄🏀🏎️ *Multi-domain detected*
This is a fascinating cross-sport comparison! 

🏀 **Basketball Legend**: Michael Jordan revolutionized the NBA...
🏎️ **Racing Legend**: Ayrton Senna was a master of Formula 1...
```

## 🚨 Troubleshooting

### Multi-Domain Not Working

1. **Check Environment Variable**:
   ```bash
   echo $USE_MULTI_DOMAIN  # Should show 'True'
   ```

2. **Verify Import**:
   ```bash
   python -c "from multi_domain_rag import MultiDomainRAG; print('✅ Import successful')"
   ```

3. **Check Logs**: Look for initialization messages:
   ```
   [+] Multi-Domain RAG system initialized successfully!
   ```

### No Domain Detection

1. **Add More Keywords**: Domain might need more specific keywords
2. **Check Source Types**: Ensure data has correct `source_type` metadata
3. **Test Detection**: Use `test_multi_domain_rag.py` to debug

### Visualizer Issues

1. **Refresh Data**: Click "🔄 Refresh Data" in sidebar
2. **Clear Filters**: Reset all filters to "All"
3. **Check F1 Data**: Ensure you have F1 data with `source_type: f1_data`

## 📈 Performance Tips

### Large Knowledge Bases

- Use domain filters to focus visualization
- Set chunk limits in visualizer (50-500 chunks)
- Enable semantic links sparingly for better performance

### Response Speed

- Domain-specific search is faster than general search
- God Commands have higher priority and faster retrieval
- Multi-domain queries take slightly longer due to cross-domain analysis

## 🤝 Contributing

### Adding New Domains

To add a new domain (e.g., NFL Football):

1. **Update `multi_domain_rag.py`**:
   ```python
   'nfl': DomainConfig(
       name="NFL Football",
       keywords=['nfl', 'football', 'patriots', 'cowboys'],
       source_types=['nfl_data'],
       god_command_prefixes=['NFL_ANALYST', 'FOOTBALL'],
       color_scheme='#013369',  # NFL blue
       emoji='🏈',
       priority_boost=1.2
   )
   ```

2. **Update Visualizer**: Add NFL data support in `rag_knowledge_visualizer.py`
3. **Test Integration**: Create test cases for NFL domain detection

### Best Practices

- Use descriptive source types (`nba_data`, `f1_data`)  
- Create domain-specific God Commands for specialized behavior
- Test domain detection with representative queries
- Monitor domain distribution in knowledge base stats

---

## 🎉 Ready to Use!

Your multi-domain Agent Daredevil is now ready to provide specialized NBA and F1 analysis! 

The system automatically routes queries to the appropriate domain expert, ensuring compartmentalized reasoning while maintaining the ability to provide cross-domain insights when relevant.

For questions or issues, check the logs or run the test script to verify everything is working correctly. 