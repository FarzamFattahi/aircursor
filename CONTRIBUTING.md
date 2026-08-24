# Contributing

Contributions that improve reliability, accessibility, documentation, or platform support are welcome.

## Local setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
```

Keep computer-vision dependencies inside `vision.py`, operating-system behavior inside `input.py`, and deterministic interaction logic in the framework-neutral modules. Add tests for changes to gesture thresholds, state transitions, coordinate mapping, or safety behavior.

## Pull requests

- Explain the user-facing behavior being changed.
- Include tests for deterministic logic.
- Describe physical webcam testing when camera or gesture behavior changes.
- Never commit recorded webcam frames, personal settings, logs, model caches, or packaged dependency folders.

