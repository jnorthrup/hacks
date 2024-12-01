# Ollm Bridge

A Python tool to create symbolic links from Ollama models to LMStudio.

## Installation

```bash
pip install ollm-bridge
```

## Usage

Simply run:

```bash
ollm-bridge
```

This will:
1. Detect your Ollama models directory
2. Detect your LMStudio models directory
3. Create symbolic links for all Ollama models in the LMStudio directory

## Requirements

- Python 3.7+
- Ollama CLI installed and in PATH
- LMStudio CLI installed and in PATH

## Model Locations

By default, Ollama stores its models in the following directories:

- macOS: `~/.ollama/models`
- Linux: `/usr/share/ollama/.ollama/models`
- Windows: `C:\Users\%username%\.ollama\models`

You can override the default location by setting the `OLLAMA_MODELS` environment variable:

```bash
# Linux/macOS
export OLLAMA_MODELS=/path/to/your/custom/directory

# Windows (via System Properties > Environment Variables)
# OLLAMA_MODELS=C:\path\to\your\custom\directory
```

## License

MIT License
