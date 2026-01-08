import re
import json
from pathlib import Path

BASE_DIR = Path(r"C:\Users\pfudi\PycharmProjects\ActiveRecallApp\AufgabenMühlbauer")

def extract_questions(text):
    results = []
    global_id = 1

    # Split by categories
    category_blocks = re.split(r'^##\s+', text, flags=re.MULTILINE)

    for block in category_blocks[1:]:
        lines = block.splitlines()
        category = lines[0].strip()

        # Split at each question
        parts = re.split(r'^###\s+Question\s+(\d+)', block, flags=re.MULTILINE)

        for i in range(1, len(parts), 2):
            qnum = int(parts[i])
            qcontent = parts[i + 1].strip()

            # Stop at next question
            qcontent = qcontent.split("### Question", 1)[0].strip()

            # 🔥 Codeblöcke (``` ... ```) entfernen
            qcontent = re.sub(r"```.*?```", "", qcontent, flags=re.DOTALL).strip()

            results.append({
                "id": global_id,
                "qid_original": qnum,
                "category": category,
                "question_raw": qcontent
            })

            global_id += 1

    return results


def main():
    extracted_dir = BASE_DIR / "extracted"
    extracted_dir.mkdir(exist_ok=True)

    # Alle Dateien durchsuchen, die z.B. "Q1stack", "Q2stack", "Q3stack" heißen
    for file in BASE_DIR.iterdir():
        if not file.is_file():
            continue

        name = file.name

        # Nur Dateien wie Q1stack, Q2stack, Q10stack ...
        if not (name.startswith("Q") and name.endswith("stack")):
            continue

        out_file = extracted_dir / f"{name}.json"

        if out_file.exists():
            print(f"⏭ Bereits extrahiert: {out_file.name}")
            continue

        print(f"🔍 Extrahiere: {name}")

        text = file.read_text(encoding="utf-8")
        questions = extract_questions(text)

        out_file.write_text(
            json.dumps(questions, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

        print(f"   ✅ Gespeichert unter: extracted/{out_file.name}")

    print("\n🎉 Fertig — alle neuen Dateien extrahiert!")


if __name__ == "__main__":
    main()
