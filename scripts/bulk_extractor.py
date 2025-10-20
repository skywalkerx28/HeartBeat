#!/usr/bin/env python3
"""
Bulk extractor for play-by-play CSVs.

Usage:
  python3 scripts/bulk_extractor.py data/processed/analytics/nhl_play_by_play/MTL/2024-2025/*.csv \
                                  data/processed/analytics/nhl_play_by_play/MTL/2025-2026/*.csv

Extracts each CSV with ComprehensiveHockeyExtractor and writes outputs to
data/processed/extracted_metrics.
"""

import sys
from pathlib import Path


def run_one(csv_path: Path, out_dir: Path) -> bool:
    try:
        from comprehensive_hockey_extraction import ComprehensiveHockeyExtractor  # type: ignore
    except Exception:
        # Fallback import path when running from scripts/
        import importlib.util
        here = Path(__file__).resolve().parent
        extractor_path = here / 'comprehensive_hockey_extraction.py'
        spec = importlib.util.spec_from_file_location('comprehensive_hockey_extraction', extractor_path)
        if not spec or not spec.loader:
            print(f"ERR: Cannot import extractor for {csv_path}")
            return False
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        ComprehensiveHockeyExtractor = getattr(mod, 'ComprehensiveHockeyExtractor')

    try:
        print(f"[EXTRACT] {csv_path}")
        extractor = ComprehensiveHockeyExtractor(str(csv_path))
        extractor.run_complete_extraction()
        extractor.save_results(str(out_dir))
        out_file = out_dir / f"{csv_path.stem}_comprehensive_metrics.json"
        ok = out_file.exists()
        print(f"[OK] {out_file}" if ok else f"[MISSING] {out_file}")
        return ok
    except Exception as e:
        print(f"[FAIL] {csv_path}: {e}")
        return False


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Usage: python3 scripts/bulk_extractor.py <glob1> [<glob2> ...]")
        return 1
    # Expand globs via shell; argv already resolved by shell
    paths = [Path(p) for p in argv[1:]]
    out_dir = Path('data/processed/extracted_metrics')
    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    ok = 0
    for p in paths:
        if p.is_file() and p.suffix.lower() == '.csv':
            total += 1
            if run_one(p, out_dir):
                ok += 1
        elif p.is_dir():
            for csv in sorted(p.glob('*.csv')):
                total += 1
                if run_one(csv, out_dir):
                    ok += 1
        else:
            # Non-file may be an unmatched glob; skip
            continue
    print(f"Completed extraction: {ok}/{total} files OK")
    return 0 if ok == total and total > 0 else 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))

