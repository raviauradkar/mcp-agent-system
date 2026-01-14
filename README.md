# MCP Agent System

A modular AI agent system with WhatsApp integration, supporting multiple LLM providers (Anthropic Claude, OpenAI, Ollama).

## Features

- **Multi-LLM Support**: Anthropic Claude, OpenAI GPT, and local Ollama models
- **MCP Tool Server**: Model Context Protocol server for tool discovery and invocation
- **WhatsApp Integration**: AI-powered WhatsApp bot via Twilio
- **HTTP API**: RESTful endpoints for all services
- **Centralized Configuration**: Single config file for all port and service settings
- **Modular Architecture**: Easily exportable and extensible components

## Architecture

```
mcp-agent-system/
├── mcp_agent/           # Core agent library
│   ├── agent.py         # Main agent implementation
│   ├── config.py        # Agent configuration
│   ├── providers.py     # LLM provider constants
│   └── llogger.py       # Logging utilities
├── services/            # Service implementations
│   ├── mcp_server.py    # MCP tool server
│   ├── user_details.py  # User data service
│   └── whatsapp.py      # WhatsApp bot service
├── scripts/             # Entry point scripts
│   ├── start_mcp_server.py
│   ├── start_user_service.py
│   ├── start_whatsapp_bot.py
│   └── agent_proxy.py   # HTTP wrapper for agent
├── examples/            # Usage examples
│   └── basic_agent.py
├── config.py            # Centralized configuration
├── pyproject.toml       # Package metadata
└── requirements.txt     # Dependencies
```

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd anthropic
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

Or install as an editable package:

```bash
pip install -e .
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your API keys
```

Required environment variables:
- `ANTHROPIC_API_KEY` - For Claude models
- `OPENAI_API_KEY` - For OpenAI models
- `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN` - For WhatsApp bot

### 4. Install Ollama (optional, for local models)

```bash
# Follow instructions at: https://ollama.ai/
ollama pull mistral:latest
```

## Usage

### Starting Services

#### MCP Server (Port 3333)
```bash
python -m services.mcp_server
# Or using entry point:
mcp-server
```

#### User Details Service (Port 8001)
```bash
python -m services.user_details
# Or:
user-details-service
```

#### Agent Proxy (Port 8000)
```bash
python scripts/agent_proxy.py [llm_provider]
# llm_provider: 0=Ollama, 1=Anthropic (default), 2=OpenAI
# Or:
agent-proxy
```

#### WhatsApp Bot (Port 5000)
```bash
python -m services.whatsapp
# Or:
whatsapp-bot
```

### Programmatic Usage

```python
import asyncio
from mcp_agent import MCPAgent, AgentConfig, LLMProvider
from config import get_config

async def main():
    config = get_config()

    agent_config = AgentConfig(
        mcp_server_url=config.MCP_SERVER_URL,
        provider=LLMProvider.ANTHROPIC,
        model="claude-sonnet-4-20250514",
        api_key=config.ANTHROPIC_API_KEY
    )

    agent = MCPAgent(agent_config)
    result = await agent.run("user123", "Get car details for +919916103095")
    print(result)

asyncio.run(main())
```

See `examples/basic_agent.py` for a complete example.

## Configuration

All service ports and settings can be configured via environment variables or the centralized `config.py`:

```python
from config import get_config

config = get_config()
print(config.MCP_SERVER_PORT)      # 3333
print(config.USER_DETAILS_PORT)    # 8001
print(config.WHATSAPP_BOT_PORT)    # 5000
print(config.AGENT_PROXY_PORT)     # 8000
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_SERVER_PORT` | 3333 | MCP server port |
| `USER_DETAILS_PORT` | 8001 | User details service port |
| `WHATSAPP_BOT_PORT` | 5000 | WhatsApp bot port |
| `AGENT_PROXY_PORT` | 8000 | Agent proxy port |
| `OLLAMA_HOST` | localhost | Ollama host |
| `OLLAMA_PORT` | 11434 | Ollama port |
| `DEFAULT_LLM_PROVIDER` | 1 | Default LLM (0=Ollama, 1=Anthropic, 2=OpenAI) |
| `LOG_LEVEL` | INFO | Logging level |
| `LOG_DIR` | logs | Log directory |

## API Endpoints

### MCP Server (Port 3333)
- `GET /` - Health check
- `GET /tools` - List available tools (OpenAI format)
- `GET /tools/simple` - List tools (simplified format)
- `POST /tools/{tool_name}` - Invoke a tool

### User Details Service (Port 8001)
- `POST /api/lookup_user_data` - Lookup user data
- `GET /health` - Health check

### Agent Proxy (Port 8000)
- `POST /generate` - Generate agent response
- `GET /health` - Health check
- `GET /llm-info` - LLM provider information

### WhatsApp Bot (Port 5000)
- `POST /webroot` - Twilio webhook for messages
- `POST /sendmessage` - Send outbound message
- `POST /sendinvite` - Send bot invitation
- `GET /site-map` - List all routes

## Logging

The project uses Python's standard `logging` library with enhanced formatting that includes:
- **Timestamp**: `%Y-%m-%d %H:%M:%S`
- **Process ID**: Useful for multi-process debugging
- **Module name**: Which component generated the log
- **Function and line number**: (file logs only) for easy debugging

### Log Format

**Console output:**
```
2026-01-14 18:00:00 - PID:12345 - mcp_agent - INFO - Your message here
```

**File output (`mcp_agent.log`):**
```
2026-01-14 18:00:00 - PID:12345 - mcp_agent - INFO - function_name:42 - Your message here
```

### Using the Logger

```python
from mcp_agent.llogger import setup_logger

# Create a logger for your module
logger = setup_logger(__name__, level="INFO")

# Log messages
logger.debug("Debug message (file only)")
logger.info("Info message (console + file)")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with stack trace")
```

See `examples/logging_demo.py` for a complete example.

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black .
```

### Type Checking
```bash
mypy .
```

## Security Notes

- Never commit `.env` file or expose API keys
- Twilio credentials are now loaded from environment variables (not hardcoded)
- All sensitive configuration should be in `.env`

## Publishing

To publish to PyPI:

```bash
python -m build
twine upload dist/*
```

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.
# mcp-agent-system
