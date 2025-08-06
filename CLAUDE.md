# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Setup

Install the package in development mode:
```bash
python3 -m pip install --editable .
```

Install development dependencies:
```bash
python3 -m pip install --editable .[dev]
```

## Common Commands

### Running Tests
```bash
python3 -m pytest game_arena/harness/
```

### Code Formatting
```bash
pyink game_arena/
```

### Linting
```bash
pylint game_arena/
```

### Running Demo
```bash
# Set API keys first (choose providers you want to use)
export GEMINI_API_KEY=your_key
export OPENAI_API_KEY=your_key
export OPENROUTER_API_KEY=your_key

# Run basic chess demo (registry models)
python3 -m game_arena.harness.harness_demo

# Run with OpenRouter models
python3 -m game_arena.harness.harness_demo \
  --player1_provider=openrouter \
  --player1_model="anthropic/claude-3.5-sonnet" \
  --player2_provider=openrouter \
  --player2_model="openai/gpt-4o-mini"

# Run with GUI (requires: pip install chess-board)
python3 -m game_arena.harness.harness_demo --gui

# Run with mixed providers and GUI
python3 -m game_arena.harness.harness_demo \
  --player1_provider=openrouter \
  --player1_model="anthropic/claude-3.5-sonnet" \
  --player2_provider=gemini \
  --player2_model="gemini-2.5-flash" \
  --gui \
  --num_moves=10
```

## Architecture Overview

This is the Google DeepMind Game Arena harness for orchestrating LLM vs LLM games. The codebase is structured around several key components:

### Core Components

1. **Game Environment** (`game_arena/harness/`)
   - Uses OpenSpiel for game state management and rules
   - Currently supports chess with extensibility for other two-player games
   - Game states tracked in canonical notation (e.g., FEN for chess)

2. **Agent System** (`agent.py`)
   - `ChessLLMAgent`: Basic LLM agent for chess gameplay
   - `ChessRethinkAgent`: Agent with rethinking capability for error recovery
   - Agents handle observation → prompt → model call → action parsing pipeline

3. **Model Generation** (`model_generation*.py`)
   - SDK-based model calling (`model_generation_sdk.py`)
   - HTTP API model calling (`model_generation_http.py`) 
   - OpenRouter integration (`model_generation_openrouter.py`)
   - Automatic retry logic with exponential backoff
   - Support for text-only and multimodal models

4. **Samplers** (`samplers.py`, `rethink.py`)
   - `MajorityVoteSampler`: Parallel sampling with self-consistency voting
   - `RethinkSampler`: Sequential sampling with error recovery
   - Used to handle illegal moves and improve reliability

5. **Parsers** (`parsers.py`, `llm_parsers.py`)
   - Rule-based parsing using regex and string manipulation
   - LLM-based parsing for free-form responses
   - Soft matching against legal moves with disambiguation

6. **Prompt Generation** (`prompt_generation.py`, `prompts.py`)
   - Template-based prompt construction
   - Support for various game state representations (text, visual, etc.)
   - Game-specific notation examples (`game_notation_examples.py`)

7. **GUI System** (`gui.py`, `gui_chess.py`)
   - Protocol-based GUI abstraction for game visualization
   - Chess-specific GUI implementation using chess-board package
   - Graceful fallback to headless mode when GUI unavailable
   - Real-time game state updates and player information display

### Key Design Patterns

- **Protocol-based interfaces**: Heavy use of Python protocols for extensibility
- **Layered architecture**: Clear separation between game logic, model calling, and parsing
- **Error resilience**: Comprehensive retry mechanisms and fallback strategies
- **Concurrent processing**: Parallel model sampling for majority voting

### Testing Structure

- Test files follow `*_test.py` naming convention
- Integration tests in `harness_demo.py` demonstrate full pipeline
- Model generation has separate test suites for SDK and HTTP implementations

### Configuration

- API keys set via environment variables (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`)
- Model options and API options passed through constructor parameters
- Game-specific configurations in `game_notation_examples.py`
- GUI support via optional `chess-board` package (install with `pip install chess-board`)

### Model Registry

The `model_registry.py` provides a centralized way to instantiate different model types with appropriate configurations for the game arena environment. 

**Supported Model Providers:**
- **OpenAI**: GPT-4.1, O3, O4-Mini models via OpenAI API
- **Anthropic**: Claude Sonnet 4, Claude Opus 4 models via Anthropic API  
- **Google**: Gemini 2.5 Flash, Gemini 2.5 Pro models via AI Studio API
- **OpenRouter**: Access to multiple model providers (Claude, GPT, etc.) via OpenRouter API
- **TogetherAI**: DeepSeek R1, Kimi K2, Qwen 3 models via TogetherAI API
- **XAI**: Grok 4 models via XAI API

**OpenRouter Integration:**
OpenRouter provides access to many LLM providers through a single API. Available models include:
- `anthropic/claude-3.5-sonnet`
- `openai/gpt-4o-mini` 
- `openrouter/horizon-beta`

Use OpenRouter in the demo with:
```bash
python3 -m game_arena.harness.harness_demo \
  --player1_provider=openrouter \
  --player1_model="anthropic/claude-3.5-sonnet"
```

**GUI Features:**
The GUI system provides visual chess board display with:
- Real-time move updates
- Player information in window titles
- Game result display
- Graceful fallback when GUI dependencies unavailable