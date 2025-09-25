# OpenAI 8-Week Sprint

**Live demo:** https://openai-8wk-sprint-api.onrender.com/ui  
**Health:** https://openai-8wk-sprint-api.onrender.com/health

## Stack
- FastAPI (Python), SQLite log, CORS, simple rate limit, optional Bearer auth
- Static UI served at `/ui`
- Render (free) deploy
- Tests: pytest + GitHub Actions CI

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app-api/requirements.txt
export MOCK_MODE=1
uvicorn app-api.main:app --host 0.0.0.0 --port 8000 --reload
```
