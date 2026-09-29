# Contributing to MADVID

Thanks for helping improve MADVID.

## Development setup

```bash
cd madvid
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -e .[dev]
```

## Project structure

- `madvid/` — reusable Python library and CLI
- `skills/madvid/` — skill metadata and terminal integration wrapper
- `tests/` — unit and smoke tests
- `docs/` — installation, configuration, and troubleshooting guides
- `examples/` — sample source fixtures

## Adding a new video style

Create a new style module under `madvid/styles/` and register it in the style registry.

## Adding a new source adapter

Implement a new source detector in `madvid/source_resolver.py` or create a dedicated adapter module and plug it into the URL/project detection flow.

## Adding AI providers

Implement a provider class under `madvid/providers.py` or a new provider module and follow the abstract interfaces.

## Testing

Run:

```bash
python3 -m pytest -q
```

## Pull requests

Keep PRs focused, include tests when behavior changes, and explain how the change helps MADVID as a reusable skill and CLI.
