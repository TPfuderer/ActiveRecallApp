# ============================================================
# 🧠 Mini Python Playground – Spaced Repetition + Difficulty + Counter
# ============================================================

import streamlit as st
import io
import contextlib
import json
import random
import time
from pathlib import Path
from streamlit_ace import st_ace

# --- Page setup ---
st.set_page_config(page_title="Mini Python Playground!", page_icon="💻", layout="centered")

# --- Load tasks from JSON ---
TASKS_PATH = Path(__file__).parent / "tasks.json"

try:
    with open(TASKS_PATH, "r", encoding="utf-8") as f:
        tasks = json.load(f)
except Exception as e:
    st.error(f"❌ Could not load tasks.json: {e}")
    st.stop()

# --- Session state initialization ---
if "task_index" not in st.session_state:
    st.session_state["task_index"] = 0
if "ratings" not in st.session_state:
    st.session_state["ratings"] = {}   # {task_id: "easy"/"medium"/"hard"}
if "attempts" not in st.session_state:
    st.session_state["attempts"] = {}  # {task_id: count}
if "review_data" not in st.session_state:
    st.session_state["review_data"] = {}  # {task_id: {"interval": days, "last_review": timestamp}}

# --- Helper functions ---
def get_task():
    return tasks[st.session_state["task_index"]]

def update_review(task_id, difficulty):
    """Adjust the review interval based on user feedback."""
    data = st.session_state["review_data"].get(task_id, {"interval": 0.5, "last_review": time.time()})
    interval = data["interval"]

    # SM-2 simplified: adjust intervals exponentially based on performance
    if difficulty == "hard":
        interval = max(interval * 0.5, 0.5)  # halve it but not below 12h
    elif difficulty == "medium":
        interval = interval * 1.5
    elif difficulty == "easy":
        interval = interval * 2.5

    st.session_state["review_data"][task_id] = {
        "interval": interval,
        "last_review": time.time(),
    }

def pick_next_task(tasks):
    """Choose the next task based on spaced repetition schedule."""
    now = time.time()
    due_tasks = []

    for task in tasks:
        tid = task["id"]
        data = st.session_state["review_data"].get(tid, {"interval": 0.5, "last_review": 0})
        last_seen = data["last_review"]
        interval_seconds = data["interval"] * 86400  # days → seconds

        if now - last_seen >= interval_seconds:  # task is due
            due_tasks.append(task)

    if not due_tasks:
        # if none are due, pick least recently reviewed
        due_tasks = sorted(tasks, key=lambda t: st.session_state["review_data"].get(t["id"], {}).get("last_review", 0))

    next_task = random.choice(due_tasks)
    return next_task

# --- Current task ---
task = get_task()

# --- Display ---
st.title(f"🧠 Task {task['id']}/{len(tasks)}")
st.markdown(f"### 📝 {task['question']}")

# --- Code editor ---
content = st_ace(
    value="# Write your code below:\n\n",
    language="python",
    theme="dracula",
    key=f"ace_editor_{task['id']}",
    height=200,
)

if st.button("▶️ Run & Check"):
    st.subheader("🖥️ Execution Result")

    tid = task["id"]
    st.session_state["attempts"][tid] = st.session_state["attempts"].get(tid, 0) + 1

    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()

    try:
        with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
            user_globals = {}
            exec(content, user_globals)

        output = stdout_buffer.getvalue()
        errors = stderr_buffer.getvalue()

        if output.strip():
            st.text_area("🖨️ Output", output, height=120)
        if errors.strip():
            st.error(errors)

        # ✅ Enhanced result checking (variables + output)
        check_vars = task.get("check_variable", [])
        expected_vals = task.get("expected_value", [])
        expected_output = task.get("expected_output", None)

        results = []

        # --- Variable checks ---
        if isinstance(check_vars, list):
            for var, exp in zip(check_vars, expected_vals):
                user_val = user_globals.get(var, None)
                if user_val == exp:
                    results.append(f"✅ `{var}` = {exp}")
                else:
                    if user_val is None:
                        results.append(f"❌ `{var}` not found.")
                    else:
                        results.append(f"❌ `{var}` = {user_val} (expected {exp})")

        elif isinstance(check_vars, str):
            user_val = user_globals.get(check_vars, None)
            if user_val == expected_vals:
                results.append(f"✅ `{check_vars}` = {expected_vals}")
            else:
                if user_val is None:
                    results.append(f"❌ `{check_vars}` not found.")
                else:
                    results.append(f"❌ `{check_vars}` = {user_val} (expected {expected_vals})")

        # --- Output check ---
        if expected_output is not None:
            if output == expected_output:
                results.append("✅ Printed output is correct.")
            else:
                results.append(
                    f"❌ Printed output was `{output.strip()}` (expected `{expected_output.strip()}`)"
                )

        # --- Display all results nicely ---
        if results:
            for line in results:
                if "✅" in line:
                    st.success(line)
                else:
                    st.warning(line)
        else:
            st.info("ℹ️ No checks defined for this task.")

    except Exception as e:
        st.error(f"❌ Exception: {e}")


st.markdown("---")

# --- Buttons: Antwort + Difficulty + Next ---
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    show_answer = st.button("💡 Antwort anzeigen")
with col2:
    hard = st.button("😤 Schwer")
with col3:
    medium = st.button("🙂 Mittel")
with col4:
    easy = st.button("😎 Einfach")
with col5:
    next_task = st.button("➡️ Nächste Aufgabe")

# --- Button logic ---
tid = task["id"]

if show_answer:
    with st.expander("💡 Lösung & Erklärung"):
        st.code(task["solution_code"], language="python")
        st.markdown(task["explanation"])

if hard:
    st.session_state["ratings"][tid] = "hard"
    update_review(tid, "hard")
    st.warning("🔴 Markiert als **Schwer** – kürzere Wiederholungsintervalle.")

if medium:
    st.session_state["ratings"][tid] = "medium"
    update_review(tid, "medium")
    st.info("🟡 Markiert als **Mittel** – normale Wiederholungsintervalle.")

if easy:
    st.session_state["ratings"][tid] = "easy"
    update_review(tid, "easy")
    st.success("🟢 Markiert als **Einfach** – längere Wiederholungsintervalle.")

# --- Next Task Selection (Spaced Repetition) ---
if next_task:
    next_t = pick_next_task(tasks)
    st.session_state["task_index"] = next_t["id"] - 1
    st.success(f"🕒 Nächste Aufgabe: #{next_t['id']} ({st.session_state['ratings'].get(next_t['id'], 'unrated')})")
    st.rerun()

# --- Fortschritt ---
progress = (st.session_state["task_index"] + 1) / len(tasks)
st.progress(progress)
st.caption(f"Aufgabe {st.session_state['task_index'] + 1} von {len(tasks)}")

# --- Statistik ---
if st.session_state["ratings"]:
    st.markdown("### 📊 Deine Bewertungen & Durchführungen:")
    for tid, rating in st.session_state["ratings"].items():
        count = st.session_state["attempts"].get(tid, 0)
        data = st.session_state["review_data"].get(tid, {})
        interval = data.get("interval", 0)
        last_review = data.get("last_review", 0)
        next_in = round(interval, 2)
        st.write(
            f"• Task {tid}: {rating.capitalize()} – {count}x durchgeführt | ⏳ Nächste Wiederholung in ~{next_in} Tagen"
        )

# ============================================================
# 📦 Fortschritt Export / Import (Minimal-Version)
# ============================================================

st.markdown("## 📦 Fortschritt speichern / laden")

# --- 1) EXPORT-BUTTON ---
if st.button("⬇️ Fortschritt als JSON herunterladen"):
    export_data = {
        "ratings": st.session_state.get("ratings", {}),
        "attempts": st.session_state.get("attempts", {}),
        "review_data": st.session_state.get("review_data", {}),
        "timestamp": time.time(),
    }
    export_str = json.dumps(export_data, indent=2, ensure_ascii=False)

    st.download_button(
        label="📥 JSON herunterladen",
        data=export_str,
        file_name="active_recall_progress.json",
        mime="application/json",
    )


# --- 2) IMPORT-BUTTON ---
uploaded = st.file_uploader("⬆️ JSON Fortschritt importieren", type="json")

if "import_done" not in st.session_state:
    st.session_state["import_done"] = False

if uploaded and not st.session_state["import_done"]:
    try:
        imported = json.load(uploaded)

        # Update states
        st.session_state["ratings"].update(imported.get("ratings", {}))
        st.session_state["attempts"].update(imported.get("attempts", {}))
        st.session_state["review_data"].update(imported.get("review_data", {}))

        # Mark import as done
        st.session_state["import_done"] = True

        st.success("✅ Fortschritt erfolgreich importiert! Seite lädt neu…")
        st.rerun()

    except Exception as e:
        st.error(f"❌ Fehler beim Import: {e}")

        st.error(f"❌ Fehler beim Import: {e}")
