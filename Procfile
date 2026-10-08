release: python -m alembic upgrade head
web: uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
