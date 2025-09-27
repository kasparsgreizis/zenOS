# 🧘 PKM Module for zenOS

Personal Knowledge Management (PKM) module for extracting, processing, and managing Google Gemini conversations.

## ✨ Features

- 🔄 **Automated Extraction**: Extract conversations from Google Gemini web interface
- 🧠 **Knowledge Processing**: Automatically extract insights, keywords, and tags
- 📚 **Smart Storage**: Store conversations in JSON and Markdown formats
- 🔍 **Powerful Search**: Search through conversations and knowledge base
- ⏰ **Cron Scheduling**: Automated extraction and processing jobs
- 📤 **Export Options**: Export data in multiple formats
- 🎯 **AI Integration**: Optional AI-powered summarization and processing

## 🚀 Quick Start

### 1. Setup PKM Module

```bash
# Setup the PKM module
zen pkm setup

# Or with custom config
zen pkm setup --config /path/to/config.yaml
```

### 2. Configure Authentication

Set your Google Gemini session cookies as environment variables:

```bash
export GEMINI_SESSION_COOKIE="your_session_cookie_here"
export GEMINI_CSRF_TOKEN="your_csrf_token_here"
```

### 3. Extract Conversations

```bash
# Extract conversations (default: 50 max)
zen pkm extract

# Extract specific number of conversations
zen pkm extract --limit 10
```

### 4. Process Knowledge

```bash
# Process conversations to extract knowledge
zen pkm process
```

### 5. Search and Explore

```bash
# List all conversations
zen pkm list

# Search conversations
zen pkm search "python programming"

# Show statistics
zen pkm stats
```

## 📋 Commands

### Core Commands

| Command | Description | Options |
|---------|-------------|---------|
| `zen pkm extract` | Extract conversations from Google Gemini | `--limit`, `--config` |
| `zen pkm list` | List extracted conversations | `--limit`, `--config` |
| `zen pkm search <query>` | Search through conversations | `--limit`, `--config` |
| `zen pkm process` | Process conversations and extract knowledge | `--config` |
| `zen pkm export` | Export data in various formats | `--format`, `--limit`, `--config` |
| `zen pkm stats` | Show storage and processing statistics | `--config` |

### Scheduling Commands

| Command | Description | Options |
|---------|-------------|---------|
| `zen pkm schedule list` | List all scheduled jobs | `--config` |
| `zen pkm schedule run <job>` | Run a specific job immediately | `--config` |
| `zen pkm schedule start` | Start the scheduler daemon | `--config` |
| `zen pkm schedule stop` | Stop the scheduler daemon | `--config` |

### Configuration Commands

| Command | Description | Options |
|---------|-------------|---------|
| `zen pkm setup` | Setup PKM module and directories | `--config` |
| `zen pkm config-show` | Show current configuration | `--config` |

## ⚙️ Configuration

The PKM module can be configured via:

1. **Environment Variables** (highest priority)
2. **Configuration file** (`~/.zenOS/pkm/config.yaml`)
3. **Default values**

### Environment Variables

```bash
# Google Gemini Authentication
export GEMINI_SESSION_COOKIE="your_session_cookie"
export GEMINI_CSRF_TOKEN="your_csrf_token"

# PKM Behavior
export PKM_AUTO_SUMMARIZE="true"
export PKM_EXTRACT_KEYWORDS="true"
export PKM_GENERATE_TAGS="true"
export PKM_STORAGE_FORMAT="both"
```

### Configuration File

Create `~/.zenOS/pkm/config.yaml`:

```yaml
# Storage Configuration
storage:
  pkm_dir: "~/.zenOS/pkm"
  conversations_dir: "~/.zenOS/pkm/conversations"
  knowledge_base_dir: "~/.zenOS/pkm/knowledge_base"
  exports_dir: "~/.zenOS/pkm/exports"
  storage_format: "both"  # json, markdown, or both
  compress_old_conversations: true
  max_storage_size_mb: 1000

# Google Gemini Configuration
gemini:
  session_cookie: ""  # Set via environment variable
  csrf_token: ""      # Set via environment variable
  user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
  base_url: "https://gemini.google.com"

# Extraction Settings
extraction:
  max_conversations_per_run: 50
  extraction_interval_hours: 6
  conversation_timeout: 30
  retry_attempts: 3

# Processing Settings
processing:
  auto_summarize: true
  extract_keywords: true
  generate_tags: true
  save_raw_html: false

# Cron Job Settings
scheduler:
  enabled: true
  cron_schedule: "0 */6 * * *"  # Every 6 hours
```

## 🏗️ Architecture

```
zen/pkm/
├── __init__.py          # Module initialization
├── agent.py             # PKM Agent for zenOS
├── cli.py               # CLI commands
├── config.py            # Configuration management
├── extractor.py         # Google Gemini extractor
├── models.py            # Data models
├── processor.py         # Conversation processing
├── scheduler.py         # Cron job scheduling
├── storage.py           # Storage and retrieval
└── README.md            # This file
```

### Data Flow

1. **Extraction**: `GeminiExtractor` → Google Gemini web interface
2. **Storage**: `PKMStorage` → Local file system (JSON/Markdown)
3. **Processing**: `ConversationProcessor` → Knowledge extraction
4. **Scheduling**: `PKMScheduler` → Automated jobs
5. **CLI**: `PKMAgent` → zenOS integration

## 📊 Data Models

### Conversation

```python
@dataclass
class Conversation:
    id: str
    title: str
    messages: List[Message]
    created_at: datetime
    updated_at: datetime
    url: Optional[str]
    status: ConversationStatus
    summary: Optional[str]
    keywords: List[str]
    tags: List[str]
    topics: List[str]
    metadata: Dict[str, Any]
```

### Knowledge Entry

```python
@dataclass
class KnowledgeEntry:
    id: str
    title: str
    content: str
    source_conversation_id: str
    source_message_index: int
    entry_type: str  # insight, fact, question, answer, code, etc.
    confidence: float
    tags: List[str]
    keywords: List[str]
    metadata: Dict[str, Any]
```

## 🔄 Scheduled Jobs

The PKM module includes several default scheduled jobs:

### Default Jobs

1. **extract_conversations** (Every 6 hours)
   - Extracts new conversations from Google Gemini
   - Configurable via `cron_schedule`

2. **process_knowledge** (Daily at 2 AM)
   - Processes conversations to extract knowledge
   - Generates summaries, keywords, and tags

3. **cleanup_old_data** (Weekly on Sunday at 3 AM)
   - Cleans up old data files
   - Compresses or removes outdated conversations

### Custom Jobs

You can add custom jobs programmatically:

```python
from zen.pkm.scheduler import PKMScheduler
from zen.pkm.config import PKMConfig

config = PKMConfig.load()
scheduler = PKMScheduler(config)

# Add a custom job
scheduler.add_job(
    name="my_custom_job",
    schedule="0 9 * * *",  # Daily at 9 AM
    function=my_custom_function,
    metadata={"description": "My custom processing job"}
)
```

## 🔍 Search Capabilities

The PKM module provides powerful search functionality:

### Conversation Search

- **Title search**: Find conversations by title
- **Content search**: Search through message content
- **Summary search**: Search through generated summaries
- **Keyword search**: Find conversations by extracted keywords

### Knowledge Base Search

- **Content search**: Search through knowledge entries
- **Tag search**: Find entries by tags
- **Type search**: Filter by entry type (code, definition, etc.)
- **Source search**: Find entries from specific conversations

## 📤 Export Options

### Supported Formats

1. **JSON**: Machine-readable format for data processing
2. **Markdown**: Human-readable format for documentation

### Export Commands

```bash
# Export all data as JSON
zen pkm export --format json

# Export conversations as Markdown
zen pkm export --format markdown --limit 10

# Export knowledge base only
zen pkm export --format json --limit 100
```

## 🛠️ Development

### Adding New Extractors

To add support for other conversation sources:

1. Create a new extractor class inheriting from a base extractor
2. Implement the extraction logic
3. Add to the PKM agent's command handling

### Adding New Processors

To add new knowledge extraction methods:

1. Extend the `ConversationProcessor` class
2. Implement new processing methods
3. Add configuration options as needed

### Custom Storage Backends

To add new storage backends:

1. Create a new storage class
2. Implement the required interface
3. Update the configuration system

## 🔒 Security Considerations

- **Session Cookies**: Store securely, never commit to version control
- **Data Privacy**: Conversations are stored locally by default
- **Authentication**: Use environment variables for sensitive data
- **Access Control**: Consider file permissions for stored data

## 🐛 Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify session cookies are valid
   - Check if Google Gemini interface has changed
   - Ensure proper user agent string

2. **Extraction Errors**
   - Check internet connection
   - Verify Google Gemini is accessible
   - Review timeout settings

3. **Processing Errors**
   - Check storage permissions
   - Verify configuration file format
   - Review log files for details

### Debug Mode

Enable debug mode for detailed logging:

```bash
export ZEN_DEBUG=true
zen pkm extract
```

## 📈 Performance

### Optimization Tips

1. **Batch Processing**: Process multiple conversations together
2. **Incremental Updates**: Only process new conversations
3. **Storage Management**: Regular cleanup of old data
4. **Caching**: Cache frequently accessed data

### Resource Usage

- **Memory**: ~10MB per 100 conversations
- **Storage**: ~1MB per 10 conversations (JSON)
- **CPU**: Minimal during extraction, moderate during processing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This module is part of zenOS and is licensed under the MIT License.

## 🙏 Acknowledgments

- Built for the zenOS AI workflow orchestration framework
- Inspired by modern PKM tools and methodologies
- Designed for seamless integration with Google Gemini conversations