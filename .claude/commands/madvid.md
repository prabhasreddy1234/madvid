---
description: Generate a product introduction video from a project, website, or app listing
argument-hint: "[url] [--duration 20] [--style minimal]"
---

Use the MADVID CLI from the current repository.

If the project environment is active, run:

```bash
madvid "$@"
```

If not yet installed, use:

```bash
source .venv/bin/activate
python -m pip install -e .
madvid "$@"
```

Examples:

```bash
madvid
madvid --preview --duration 20 --style minimal
madvid https://example.com
madvid "https://play.google.com/store/apps/details?id=com.example.app"
```
