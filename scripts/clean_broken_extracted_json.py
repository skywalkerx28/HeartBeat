"""
Remove malformed extracted metrics JSON files from GCS bronze tier (Option A).

Usage:
  python scripts/clean_broken_extracted_json.py \
    --file playsequence-20251018-NHL-TBLvsCBJ-20252026-20082_comprehensive_metrics.json

This deletes:
  - gs://<BUCKET>/bronze/extracted_metrics/season=<SEASON>/<FILE>
  - gs://<BUCKET>/bronze/extracted_metrics/by_team/season=<SEASON>/team=<TEAM>/*.pointer.json (for both teams)
"""

import argparse
import os
import re
from google.cloud import storage


def infer_season_from_name(name: str) -> str:
    m = re.search(r"-(20\d{2})(\d{2})-\d+", name)
    if m:
        return f"{m.group(1)}{m.group(2)}"
    m2 = re.search(r"playsequence-(\d{4})(\d{2})(\d{2})", name)
    if m2:
        y = int(m2.group(1)); mm = int(m2.group(2))
        start = y if mm >= 10 else y - 1
        return f"{start}{start+1}"
    return "unknown"


def infer_teams_from_name(name: str):
    m = re.search(r"-([A-Z]{2,3})vs([A-Z]{2,3})-", name)
    if m:
        return m.group(1), m.group(2)
    return None, None


def delete_object(bucket: storage.Bucket, path: str) -> bool:
    blob = bucket.blob(path)
    if not blob.exists():
        return False
    blob.delete()
    return True


def main():
    parser = argparse.ArgumentParser(description="Remove malformed extracted metrics JSON from GCS")
    parser.add_argument("--file", required=True, help="Filename of the bad JSON (basename only)")
    parser.add_argument("--bucket", default=os.getenv("GCS_LAKE_BUCKET", "heartbeat-474020-lake"))
    args = parser.parse_args()

    season = infer_season_from_name(args.file)
    team_a, team_b = infer_teams_from_name(args.file)

    client = storage.Client(project=os.getenv("GCP_PROJECT", "heartbeat-474020"))
    bucket = client.bucket(args.bucket)

    removed = 0
    # Canonical payload
    payload_path = f"bronze/extracted_metrics/season={season}/{args.file}"
    if delete_object(bucket, payload_path):
        print(f"Deleted: gs://{args.bucket}/{payload_path}")
        removed += 1
    else:
        print(f"Not found: gs://{args.bucket}/{payload_path}")

    # Team pointers
    pointer_name = args.file.replace(".json", ".pointer.json")
    for team in (team_a, team_b):
        if not team:
            continue
        p = f"bronze/extracted_metrics/by_team/season={season}/team={team}/{pointer_name}"
        if delete_object(bucket, p):
            print(f"Deleted: gs://{args.bucket}/{p}")
            removed += 1
        else:
            print(f"Not found: gs://{args.bucket}/{p}")

    print(f"Done. Objects removed: {removed}")


if __name__ == "__main__":
    main()

