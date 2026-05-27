# AudioForge — Dev & Production

Dev (run backend + frontend separately)
1. Create venv and install backend deps:
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
2. Start backend:
   python app.py
3. Start frontend:
   cd frontend
   npm install
   npm run dev

Production (single process serving build)
1. Build frontend:
   cd frontend
   npm ci
   npm run build
2. Ensure `frontend/dist/` exists, then start backend:
   python app.py
3. The backend serves API + static frontend at `/`.

Notes:
- Long-running stem separation currently blocks the request; consider using BackgroundTasks, a task queue (Celery/RQ), or worker processes for non-blocking jobs.
- Use `uvicorn api:app --host 0.0.0.0 --port 8000` for production with process manager / container.
