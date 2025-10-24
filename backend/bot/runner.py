"""
HeartBeat.bot - Cloud Run Job Runner (Path B)

Runs HeartBeat bot tasks synchronously in a one-shot process so they can be
scheduled via Cloud Run Jobs + Cloud Scheduler. This avoids running long-lived
Celery workers in production while reusing the same task logic.

Usage examples (inside the backend image):

  python -m bot.runner collect-transactions
  python -m bot.runner collect-injury-reports
  python -m bot.runner collect-team-news
  python -m bot.runner collect-game-summaries
  python -m bot.runner aggregate-news
  python -m bot.runner generate-daily-article
  python -m bot.runner ontology-refresh

Exit code is 0 on success, 1 on error. Results (if any) are printed as JSON.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from typing import Any, Callable, Dict
import os
from pathlib import Path


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _load_task_map() -> Dict[str, Callable[[], Any]]:
    """Return a mapping of runner command -> callable that executes synchronously.

    We call Celery task objects' .run() methods directly to execute inline without
    a broker/worker. This provides a bound task instance so internal `self.retry`
    calls raise exceptions we can catch and report as failures.
    """
    # Ensure repo root is on sys.path so 'orchestrator' package is importable
    try:
        repo_root = Path(__file__).resolve().parents[2]
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
    except Exception:
        pass

    from . import tasks as bot_tasks

    try:
        # Ontology refresh (optional). Use plain function if available.
        from orchestrator.tasks.ontology_refresh import daily_ontology_refresh
        ontology_callable = daily_ontology_refresh
    except Exception:  # pragma: no cover - optional dependency
        ontology_callable = lambda: {"skipped": True, "reason": "ontology module unavailable"}

    return {
        "collect-transactions": bot_tasks.collect_transactions,
        "collect-injury-reports": bot_tasks.collect_injury_reports,
        "collect-team-news": bot_tasks.collect_team_news,
        "collect-game-summaries": bot_tasks.collect_game_summaries,
        "aggregate-news": bot_tasks.aggregate_and_synthesize_news,
        "generate-daily-article": bot_tasks.generate_daily_article,
        "ontology-refresh": ontology_callable,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HeartBeat.bot task runner")
    parser.add_argument(
        "task",
        choices=[
            "collect-transactions",
            "collect-injury-reports",
            "collect-team-news",
            "collect-game-summaries",
            "aggregate-news",
            "generate-daily-article",
            "ontology-refresh",
        ],
        help="Task to execute",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args(argv)

    _setup_logging(args.verbose)

    tasks = _load_task_map()
    fn = tasks[args.task]

    try:
        result = fn()
        # Ensure JSON-serializable output
        try:
            print(json.dumps({"task": args.task, "ok": True, "result": result}, default=str))
        except Exception:
            print(json.dumps({"task": args.task, "ok": True, "result": str(result)}))
        return 0
    except Exception as e:  # pragma: no cover - safety
        logging.exception("Task execution failed")
        print(json.dumps({"task": args.task, "ok": False, "error": str(e)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
