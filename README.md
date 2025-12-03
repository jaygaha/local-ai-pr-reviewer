# Local AI Reviewer

An automated code review tool that uses local Large Language Models to analyze Git branch changes. Reviews run entirely on your machine using Docker or Ollama, keeping your code private.

## Features

- **Private & Local**: All processing happens on your machine
- **Smart Analysis**: Automatically detects and reviews changed files between branches
- **Handles Large Files**: Splits large diffs into manageable chunks
- **Clean Interface**: Progress bars and formatted terminal output
- **Markdown Reports**: Saves findings to `PR_REVIEW.md`

## Prerequisites

- Python 3.8+
- Git
- Docker or Ollama with a local LLM model
- Recommended: GPU or Apple Silicon for better performance

## Installation

1. **Clone and navigate to the repository**
```bash
   git clone git@github.com:jaygaha/local-ai-pr-reviewer.git
   cd local-ai-pr-reviewer
```

2. **Create a virtual environment**
```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**
```bash
   pip install -r requirements.txt
```

4. **Configure environment**
```bash
   cp .env-example .env  # On Windows: copy .env-example .env
```

5. **Pull an LLM model**
```bash
   docker model pull ai/qwen3-coder:latest
   # or
   ollama pull deepseek-coder:6.7b
```

## Configuration

Edit `.env` to customize:

- `OLLAMA_URL`: API endpoint (e.g., `http://localhost:11434/api/chat`)
- `AI_MODEL`: Model name (e.g., `ai/deepseek-coder:6.7b`)
- `CHUNK_LIMIT`: Max characters before splitting diffs (default: `3000`)

## Setup Git Alias

Create a convenient Git alias for easy access:
```bash
git config --global alias.ai-review '!f() { source /path/to/local-ai-pr-reviewer/.venv/bin/activate; python3 /path/to/local-ai-pr-reviewer/reviewer.py "$1" "$2"; }; f'
```

Replace `/path/to/` with your actual installation path.

## Usage
```bash
git fetch origin
git ai-review main feature-branch
```

The tool generates a `PR_REVIEW.md` report with findings, or displays "No issues found" if the code looks good.

## Troubleshooting

**Connection refused**: Ensure Docker/Ollama is running and `OLLAMA_URL` is correct

**Git errors**: Verify you're in a Git repository and branch names exist

**Model not found**: Pull the model with `docker model pull` or `ollama pull`

## Support

Open an issue in the repository for bugs or feature requests.