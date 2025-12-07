import json
from pathlib import Path

# Path to your tasks.json
path = Path(r"C:\Users\Tristan\PycharmProjects\ActiveRecallApp\app\tasks.json")

# Load JSON
with open(path, "r", encoding="utf-8") as f:
    tasks = json.load(f)

# Overwrite id with qid_original
for task in tasks:
    if "qid_original" in task:
        task["id"] = int(task["qid_original"])
    else:
        print("Warning: task missing qid_original:", task)

# Save JSON back to file
with open(path, "w", encoding="utf-8") as f:
    json.dump(tasks, f, indent=2, ensure_ascii=False)

print("✔ Done! ID has been overwritten with qid_original for all tasks.")
