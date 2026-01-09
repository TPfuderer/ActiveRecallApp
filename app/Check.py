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

if __name__ == "__main__":
    check_missing_ids(TASKS_PATH, key="id")
