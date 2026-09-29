# Installation

## Requirements

- Python 3.10+
- An AI terminal or shell that can run the `madvid` command

## Install from source

```bash
cd madvid
python3 -m pip install -e .
```

## Register as a skill

Install the skill for Claude Code with the helper. It defaults to
`~/.claude/skills/madvid`; pass a different skills directory as the first argument
for another AI terminal:

```bash
./scripts/install.sh
# Or, for a different AI terminal:
./scripts/install.sh /path/to/skills
```

After reloading Claude Code, invoke `/madvid`.
