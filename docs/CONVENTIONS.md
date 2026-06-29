# CONVENTIONS.md — support-agent

Coding patterns the agent follows. Hard *invariants* live in CLAUDE.md and are
enforced by check_boundaries.py; this file is the rest.

## Secrets
- Keys live in `.env` locally (gitignored) and the host's secret store when
  deployed. Never hard-code a key; never commit `.env`.
- Code reads keys via `os.environ[...]` after `load_dotenv()`. verify.sh sources
  `.env` so the smoke test can see GROQ_API_KEY.

## Model calls
- All model calls go through the Groq client in agent.py and MUST use
  `call_model_with_retry` (exponential backoff on 429) — the free tier rate-limits.
- Default to the small model (`llama-3.1-8b-instant`) unless a task needs more.

## Memory code
- All DB access lives in memory.py. Other modules call its functions; they never
  open a sqlite connection.
- Any function with an LLM step takes an injectable `summarizer` callable
  (default = real model call), so tests run offline.

## Tests
- Deterministic and offline: pass stub callables for LLM steps.
- Assert STRUCTURAL properties of generated text (non-empty, length bound,
  contains a known fact), never exact wording.
- New behavior ships with a test named in a feature's verification_command.

## Style
- `ruff check .` must pass (verify.sh enforces it).
- Small functions, clear names over comments.