import json
from pathlib import Path

# Path to your tasks file
TASKS_PATH = Path(r"C:\Users\pfudi\PycharmProjects\ActiveRecallApp\app\tasks.json")

def check_missing_ids(path: Path, key: str = "id"):
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    ids = sorted(task[key] for task in tasks)

    missing = []
    for prev, curr in zip(ids, ids[1:]):
        if curr != prev + 1:
            missing.extend(range(prev + 1, curr))

    if missing:
        print("⚠️ Missing IDs detected:")
        print(missing)
    else:
        print("✅ No missing IDs. Sequence is continuous.")

from collections import Counter

def check_duplicate_ids(path: Path, key: str = "id"):
    with open(path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    ids = [task[key] for task in tasks]
    counts = Counter(ids)

    duplicates = {k: v for k, v in counts.items() if v > 1}

    if duplicates:
        print("🚨 Duplicate IDs detected:")
        for k, v in duplicates.items():
            print(f"  ID {k} appears {v} times")
    else:
        print("✅ No duplicate IDs found.")

if __name__ == "__main__":
    # existing checks
    check_missing_ids(TASKS_PATH, key="id")
    check_missing_ids(TASKS_PATH, key="qid_original")

    # NEW: duplicate check
    check_duplicate_ids(TASKS_PATH, key="id")
    check_duplicate_ids(TASKS_PATH, key="qid_original")

