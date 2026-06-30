# Contributing

Use Python 3.11 for local development and install the editable development environment.

macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

Before committing, run:

```bash
pytest --cov
ruff check .
mypy src
```

Do not commit raw datasets, processed datasets, trained model binaries, credentials, or
generated report figures. Keep changes small enough that their physical and security
assumptions can be reviewed explicitly.
