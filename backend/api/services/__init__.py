"""
HeartBeat Engine - API Services package

Notes:
- Avoid importing heavy/optional orchestrator implementations at package import time.
- Services are imported lazily by route modules to keep startup robust when
  certain backends (e.g., Qwen3) are not installed or enabled.
"""

# Intentionally no eager imports here.
