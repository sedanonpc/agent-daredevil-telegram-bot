# Agent Daredevil - Development Guide

**Version**: 1.0.0  
**Last Updated**: 2024

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Code Style Guidelines](#code-style-guidelines)
4. [Testing Guidelines](#testing-guidelines)
5. [Debugging](#debugging)
6. [Adding New Features](#adding-new-features)
7. [Contributing](#contributing)

---

## 1. Getting Started

### 1.1 Prerequisites

- Python 3.8+ (3.11 recommended)
- Git
- Virtual environment tool (venv, virtualenv, or conda)
- IDE (VS Code, PyCharm, etc.)
- Telegram API credentials
- LLM provider API key

### 1.2 Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd agent-daredevil-telegram-bot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies (optional)
pip install pytest black flake8 mypy

# Configure environment
cp env.example .env
# Edit .env with your credentials
```

### 1.3 Verify Setup

```bash
# Check Python version
python --version  # Should be 3.8+

# Check dependencies
python -c "import telethon, openai, fastapi; print('OK')"

# Test LLM provider
python check_llm_provider.py

# Run bot (test mode)
python telegram_bot_rag.py
```

---

## 2. Development Workflow

### 2.1 Branch Strategy

**Main Branches**:
- `main`: Production-ready code
- `develop`: Development branch (if using Git Flow)

**Feature Branches**:
- `feature/feature-name`: New features
- `bugfix/bug-name`: Bug fixes
- `hotfix/issue-name`: Critical fixes

**Example**:
```bash
# Create feature branch
git checkout -b feature/new-llm-provider

# Make changes
# ...

# Commit changes
git add .
git commit -m "feat: add new LLM provider"

# Push branch
git push origin feature/new-llm-provider

# Create pull request
```

### 2.2 Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(llm): add Claude provider support
fix(memory): resolve session timeout issue
docs(api): update API reference
refactor(rag): optimize vector search
```

### 2.3 Code Review Process

1. **Create Pull Request**
2. **Self-Review**: Check your own code first
3. **Request Review**: Assign reviewers
4. **Address Feedback**: Make requested changes
5. **Merge**: After approval

**Review Checklist**:
- [ ] Code follows style guidelines
- [ ] Tests pass (if applicable)
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Error handling implemented
- [ ] Logging added where appropriate

---

## 3. Code Style Guidelines

### 3.1 Python Style

Follow [PEP 8](https://pep8.org/):

**Key Rules**:
- Use 4 spaces for indentation
- Maximum line length: 100 characters
- Use descriptive variable names
- Add docstrings to functions/classes
- Use type hints where possible

**Example**:
```python
def generate_response(
    self,
    message_text: str,
    user_id: int,
    is_voice: bool = False
) -> str:
    """
    Generate AI response with RAG context.
    
    Args:
        message_text: User's message text
        user_id: User identifier
        is_voice: Whether message is from voice
        
    Returns:
        Generated response text
        
    Raises:
        ValueError: If message is empty
    """
    if not message_text:
        raise ValueError("Message text cannot be empty")
    
    # Implementation...
    return response
```

### 3.2 Formatting

**Use Black**:
```bash
# Format code
black .

# Check formatting
black --check .
```

**Use isort** (optional):
```bash
# Sort imports
isort .
```

### 3.3 Linting

**Use flake8**:
```bash
# Lint code
flake8 .

# With configuration
flake8 --config=.flake8 .
```

**Use mypy** (type checking, optional):
```bash
# Type check
mypy .
```

### 3.4 Documentation

**Docstring Format** (Google style):
```python
def function_name(param1: str, param2: int) -> str:
    """Short description.
    
    Longer description if needed.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When something goes wrong
    """
    pass
```

**Inline Comments**:
```python
# Good: Explain why, not what
# Retry logic for transient API failures
if retry_count < 3:
    response = await api_call()

# Bad: Obvious comment
# Increment counter
counter += 1
```

---

## 4. Testing Guidelines

### 4.1 Test Structure

**Unit Tests**:
- Test individual functions/methods
- Mock external dependencies
- Fast execution

**Integration Tests**:
- Test component interactions
- Use test databases
- Slower execution

**Example Structure**:
```
tests/
├── unit/
│   ├── test_llm_provider.py
│   ├── test_session_memory.py
│   └── test_voice_processor.py
├── integration/
│   ├── test_bot_engine.py
│   └── test_web_api.py
└── conftest.py  # Pytest configuration
```

### 4.2 Writing Tests

**Example**:
```python
import pytest
from llm_provider import OpenAIProvider

@pytest.fixture
def openai_provider():
    return OpenAIProvider(
        api_key="test_key",
        model="gpt-4"
    )

@pytest.mark.asyncio
async def test_generate_response(openai_provider):
    messages = [
        {"role": "user", "content": "Hello"}
    ]
    
    response = await openai_provider.generate_response(messages)
    
    assert response is not None
    assert len(response) > 0
```

### 4.3 Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_llm_provider.py

# Run with coverage
pytest --cov=. --cov-report=html

# Run with verbose output
pytest -v
```

### 4.4 Test Best Practices

1. **Test Names**: Descriptive, test_what_should_happen
2. **Arrange-Act-Assert**: Clear test structure
3. **Isolation**: Tests should not depend on each other
4. **Mocking**: Mock external APIs/databases
5. **Coverage**: Aim for 80%+ code coverage

---

## 5. Debugging

### 5.1 Enable Debug Mode

**Environment Variable**:
```env
DEBUG=True
LOG_LEVEL=DEBUG
```

**In Code**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 5.2 Logging

**Structured Logging**:
```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred", exc_info=True)
```

**Log Files**:
- `telegram_bot_rag.log`: Bot logs
- `web_messenger.log`: Web API logs

**View Logs**:
```bash
# Tail logs
tail -f telegram_bot_rag.log

# Search logs
grep "ERROR" telegram_bot_rag.log

# View last 100 lines
tail -n 100 telegram_bot_rag.log
```

### 5.3 Debugging Tools

**Python Debugger (pdb)**:
```python
import pdb

def function():
    pdb.set_trace()  # Breakpoint
    # Code execution pauses here
```

**VS Code Debugging**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Bot",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/telegram_bot_rag.py",
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env"
    }
  ]
}
```

### 5.4 Common Debugging Scenarios

**API Errors**:
```python
try:
    response = await api_call()
except Exception as e:
    logger.error(f"API call failed: {e}", exc_info=True)
    # Check API key, network, rate limits
```

**Database Issues**:
```python
# Check database connection
import sqlite3
conn = sqlite3.connect('memory.db')
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM messages")
print(cursor.fetchone())
```

**Memory Issues**:
```python
import sys
print(f"Memory usage: {sys.getsizeof(object)} bytes")
```

---

## 6. Adding New Features

### 6.1 Feature Development Process

1. **Plan**: Design feature architecture
2. **Branch**: Create feature branch
3. **Implement**: Write code
4. **Test**: Add tests
5. **Document**: Update documentation
6. **Review**: Create pull request
7. **Merge**: After approval

### 6.2 Adding New LLM Provider

**Step 1**: Create provider class
```python
# llm_provider.py

class NewProvider(LLMProvider):
    def __init__(self, api_key: str, model: str):
        # Initialize client
        pass
    
    async def generate_response(self, messages, ...):
        # Implement generation logic
        pass
    
    def get_model_name(self) -> str:
        return "new-provider-model"
```

**Step 2**: Add factory method
```python
def get_llm_provider() -> LLMProvider:
    provider = os.getenv('LLM_PROVIDER')
    # ... existing providers ...
    elif provider == 'new_provider':
        return NewProvider(...)
```

**Step 3**: Update environment template
```env
# env.example
NEW_PROVIDER_API_KEY=your_key
NEW_PROVIDER_MODEL=model_name
```

**Step 4**: Add tests
```python
# tests/unit/test_llm_provider.py
def test_new_provider():
    # Test implementation
    pass
```

**Step 5**: Update documentation
- Add to `spec.md`
- Add to `HANDOVER.md`
- Update `README.md`

### 6.3 Adding New API Endpoint

**Step 1**: Define endpoint
```python
# web_messenger_server.py

@app.post("/api/new-endpoint")
async def new_endpoint(request: NewRequest):
    """New endpoint description."""
    # Implementation
    return NewResponse(...)
```

**Step 2**: Define models
```python
class NewRequest(BaseModel):
    field1: str
    field2: int

class NewResponse(BaseModel):
    result: str
```

**Step 3**: Add tests
```python
# tests/integration/test_web_api.py
def test_new_endpoint():
    response = client.post("/api/new-endpoint", json={...})
    assert response.status_code == 200
```

**Step 4**: Update API documentation
- Add to `API_REFERENCE.md`

### 6.4 Code Review Checklist

Before submitting PR:
- [ ] Code follows style guidelines
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
- [ ] Error handling implemented
- [ ] Logging added
- [ ] Environment variables documented

---

## 7. Contributing

### 7.1 Contribution Process

1. **Fork** repository (if external)
2. **Create** feature branch
3. **Make** changes
4. **Test** changes
5. **Document** changes
6. **Submit** pull request

### 7.2 Code of Conduct

- Be respectful
- Provide constructive feedback
- Follow project guidelines
- Maintain code quality

### 7.3 Pull Request Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests added/updated
- [ ] Manual testing performed

## Checklist
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

---

## Appendix: Useful Commands

### Development Commands

```bash
# Format code
black .

# Lint code
flake8 .

# Type check
mypy .

# Run tests
pytest

# Run bot
python telegram_bot_rag.py

# Run web server
python launch_web_messenger.py

# Check provider
python check_llm_provider.py
```

### Git Commands

```bash
# Create feature branch
git checkout -b feature/name

# Commit changes
git add .
git commit -m "feat: description"

# Push branch
git push origin feature/name

# Update from main
git checkout main
git pull
git checkout feature/name
git merge main
```

### Docker Commands

```bash
# Build image
docker build -t agent-daredevil .

# Run container
docker run -d --env-file .env agent-daredevil

# View logs
docker logs agent-daredevil

# Stop container
docker stop agent-daredevil
```

---

**Document Version**: 1.0.0  
**Last Updated**: 2024

