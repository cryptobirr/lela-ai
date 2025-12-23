# Lela AI - Composable Agent Harness

Pod-based composable agent architecture for LLM-agnostic task orchestration.

## Overview

A **Pod-based** system where Pods chain together to accomplish complex goals. Each component is LLM-agnostic.

**Pod Definition:** `POD = 1 Supervisor + 1...N Workers`

- Supervisors per pod: Exactly 1
- Workers per pod: 1 or more
- Communication: Disk only (file-based)

## Prerequisites

- Python 3.11+
- uv (https://docs.astral.sh/uv/)

## Quick Start

### 1. Install dependencies

```bash
uv sync
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your LLM API keys
```

### 3. Run the application

```bash
uv run python src/main.py
```

## Development

### Linting and formatting

```bash
# Check code
uv run ruff check src/

# Format code
uv run ruff format src/

# Fix issues automatically
uv run ruff check --fix src/
```

### Run tests

```bash
uv run pytest dev/testing/
```

## Project Structure

```
lela-ai/
├── dev/              # Development artifacts (gitignored)
│   ├── testing/      # Test files
│   ├── issues/       # Issue-specific work
│   ├── specs/        # Specifications
│   └── temp/         # Temporary files
├── src/              # Source code
│   ├── supervisor/   # Supervisor agents
│   ├── workers/      # Worker agents
│   └── core/         # Core orchestration logic
├── .env.example      # Environment template
├── ruff.toml         # Ruff configuration
└── pyproject.toml    # Project metadata
```

## Architecture

### Single Pod

```
┌─────────────────────────────────────────────┐
│                    POD                       │
│                                              │
│  ┌────────────┐      ┌────────────┐         │
│  │ Supervisor │ ───→ │  Worker 1  │         │
│  │            │ ───→ │  Worker 2  │         │
│  │ (1 only)   │ ───→ │  Worker N  │         │
│  └────────────┘      └────────────┘         │
│        ↑                   │                 │
│        └───────────────────┘                 │
│            file-based loop                   │
└─────────────────────────────────────────────┘
```

### Chained Pods

```
┌─────────┐     ┌─────────┐     ┌─────────┐
│  POD A  │ ──→ │  POD B  │ ──→ │  POD C  │
└─────────┘     └─────────┘     └─────────┘
   output          output          output
   file A    →     file B    →     file C
```

## License

MIT
