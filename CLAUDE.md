# Claude Code Project Instructions

## Tech Stack

- **Language:** Python 3.11+
- **Package Manager:** uv
- **Linter/Formatter:** ruff

## Development Workflow

**Directory structure:** See `~/.claude/skills/project-directory-structure.md`

- All development files go in `dev/` folder
- Source code in `src/`
- Tests in `dev/testing/`
- Issue-specific work in `dev/issues/NNN-name/`

## Common Commands

```bash
# Install dependencies
uv sync

# Run application
uv run python src/main.py

# Lint
uv run ruff check src/

# Format
uv run ruff format src/

# Fix automatically
uv run ruff check --fix src/

# Run tests
uv run pytest dev/testing/
```

## Coding Standards

- Line length: 100 characters
- Formatter: ruff (auto on save in VS Code)
- Linter: ruff (select rules: E, F, I, W, N)
- Target: Python 3.11+

## Project Context

This is a **composable agent harness** with pod-based architecture:

- **Pod** = 1 Supervisor + 1...N Workers
- **Supervisor**: Binary evaluator (PASS/FAIL) - compares instructions to results
- **Workers**: Execute tasks, write results
- **Communication**: File-based only (instructions.json, result.json, feedback.json)
- **LLM-agnostic**: Each agent can use different LLM providers

### Key Design Principles

1. **Binary evaluation** - No ambiguity, no drift (100% compliance or reject)
2. **File-based communication** - Stateless, debuggable, resumable
3. **LLM-agnostic** - Mix providers freely within pods
4. **Chainable pods** - Complex workflows from simple units
5. **Quality gates** - Each pod guarantees output meets instructions

## File Contracts

**instructions.json** (Supervisor writes):
```json
{
  "instructions": "exactly what must be done",
  "output_path": "result.json"
}
```

**result.json** (Worker writes):
```json
{
  "result": "..."
}
```

**feedback.json** (Supervisor writes on FAIL):
```json
{
  "status": "FAIL",
  "gaps": ["Missing X", "Y does not match requirement Z"],
  "attempt": 2
}
```

**On PASS**:
```json
{
  "status": "PASS",
  "result": "...",
  "attempts": 2
}
```

## Architecture Guidelines

When implementing features:

1. **Keep supervisors dumb** - They only compare instructions to results
2. **Make workers stateless** - Read input, produce output, no memory
3. **Use file contracts** - Strictly follow JSON schemas
4. **Enable pod chaining** - Output of one pod is input to next
5. **Support LLM flexibility** - Don't hardcode provider assumptions

## Source Code Organization

```
src/
├── supervisor/       # Supervisor implementation
├── workers/          # Worker implementations
├── core/             # Core orchestration
│   ├── pod.py        # Pod management
│   ├── evaluator.py  # Instruction/result comparison
│   └── chain.py      # Multi-pod orchestration
└── utils/            # Shared utilities
```
