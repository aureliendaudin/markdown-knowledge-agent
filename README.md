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

Install Python packages

```
pip install -r requirements.txt
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
- **modules**: Enable/disable modules (retrieval, memory, reasoning)
- **logging**: Log level and output configuration
- **tools**: Tool-specific parameters

See `config.yaml.example` for all available options with comments.


## Run
```
python main.py
```

## Roadmap

- [x] Documentary retrieval module
- [ ] Short/long-term memory module
- [ ] Reasoning & reflection module
- [ ] Query planning module
- [ ] Multi-document synthesis

## Contributing

- Angela Saade
- Aurélien Daudin
- Baptiste Arnold
- Khaled Mili