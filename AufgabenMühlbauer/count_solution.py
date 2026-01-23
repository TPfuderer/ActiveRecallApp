import json
from pathlib import Path

path = Path(r"C:\Users\pfudi\PycharmProjects\ActiveRecallApp\app\tasks.json")
out = path.with_name("extracted_solutions.txt")

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

solutions = [item["solution_code"] for item in data if "solution_code" in item]

with open(out, "w", encoding="utf-8") as f:
    for i, sol in enumerate(solutions, 1):
        f.write(f"# ===== Solution {i} =====\n")
        f.write(sol.strip())
        f.write("\n\n")

count_solution = len(solutions)

if count_solution == 460:
    print("OK")
else:
    print(False, count_solution)
