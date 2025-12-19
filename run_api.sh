#!/bin/bash
# Activate virtual environment
source .venv/bin/activate

# Run the API server
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
