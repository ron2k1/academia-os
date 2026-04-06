# AcademiaOS

Docker-packaged multi-agent academic workspace. A FastAPI backend + React frontend
where a lead orchestrator routes user intent to specialized sub-agents, each running
as a fresh Claude CLI subprocess with context injected from Obsidian-style vaults.

## Quickstart

```bash
pip install -r requirements.txt
cp config/classes.example.json config/classes.json
cp config/models.example.json config/models.json
python scripts/init_semester.py --config config/classes.json
python -m pytest tests/ -v
```
