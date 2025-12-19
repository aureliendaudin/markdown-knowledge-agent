# markdown-knowledge-agent

## Installation

Install Ollama 

```
curl -fsSL https://ollama.com/install.sh | sh
```

Download a model for tool calling

```
ollama pull qwen2.5:3b
```

Install Python packages using uv

```
uv sync
```

## Configuration

### 1. Create Configuration File

```
cp config.yaml.example config.yaml
```

### 2. Edit Configuration

Open `config.yaml` and set your parameters:

```
vault:
path: /home/aurelien/Documents/ObsidianVault # Your vault path

model:
provider: ollama # or 'anthropic'
ollama:
model: qwen2.5:3b

logging:
level: INFO # DEBUG for verbose output
```

### 3. Configuration Sections

- **vault**: Obsidian vault location and indexing options
- **model**: LLM provider and model settings
- **agent**: Agent behavior (iterations, timeout)
- **modules**: Enable/disable modules (retrieval, planning, memory, reasoning)
  - **retrieval**: Documentary search and retrieval
  - **planning**: Planner-Executor pattern for complex query decomposition
- **logging**: Log level and output configuration
- **tools**: Tool-specific parameters

#### Planning Module (Optional)

The planning module implements the Planner-Executor pattern, which decomposes complex queries into structured sub-tasks:

```yaml
modules:
  planning:
    enabled: true  # Enable Planner-Executor pattern
    max_subtasks: 10
    max_retries_per_task: 2
    verification_mode: flexible  # or 'strict'
```

**Benefits:**
- Better traceability of agent decisions
- Improved error handling and retry logic
- Easier debugging with structured execution plans

See `config.yaml.example` for all available options with comments.


## Run
```
uv run python main.py
```

## Roadmap

- [x] Documentary retrieval module
- [x] Query planning module (Planner-Executor pattern)
- [ ] Short/long-term memory module
- [ ] Reasoning & reflection module
- [ ] Multi-document synthesis

## Contributing

- Angela Saade
- Aurélien Daudin
- Baptiste Arnold
- Khaled Mili