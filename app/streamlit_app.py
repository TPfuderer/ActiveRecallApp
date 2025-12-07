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
import requests
import json
from supabase import create_client
import json

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

# ============================================================
# 🔧 BUILD QID LOOKUP TABLES (NEW)
# ============================================================
qid_to_task = {}
qid_to_index = {}

for idx, task in enumerate(tasks):
    qid = int(task.get("qid_original", idx + 1))  # fallback if missing
    task["_index"] = idx
    qid_to_task[qid] = task
    qid_to_index[qid] = idx


supabase = create_client(
    st.secrets["SUPABASE_URL"],
    st.secrets["SUPABASE_ANON_KEY"]
)

st.write("Supabase connected:", supabase is not None)


# --- Tabs ----------------------------------------------------
tabs = st.tabs(["🧠 Aufgaben", "❗ Issue melden", "📊 Dashboard"])

# ============================================================
# 🧠 TAB 1: Aufgaben & Learning UI
# ============================================================
with tabs[0]:

    # ============================================================
    # Session state initialization (patched to use qid_original)
    # ============================================================

    if "task_index" not in st.session_state:
        random_qid = random.choice(list(qid_to_index.keys()))
        st.session_state["task_index"] = qid_to_index[random_qid]

    if "ratings" not in st.session_state:
        st.session_state["ratings"] = {}
    if "attempts" not in st.session_state:
        st.session_state["attempts"] = {}
    if "review_data" not in st.session_state:
        st.session_state["review_data"] = {}

    if "filter_changed" not in st.session_state:
        st.session_state["filter_changed"] = False
    if "prev_filter_mode" not in st.session_state:
        st.session_state["prev_filter_mode"] = None
    if "prev_cat" not in st.session_state:
        st.session_state["prev_cat"] = None
    if "prev_qid" not in st.session_state:
        st.session_state["prev_qid"] = None


    # ============================================================
    # Helper functions
    # ============================================================

    def get_task():
        return tasks[st.session_state["task_index"]]


    def username_exists(username):
        res = supabase.table("users").select("username").eq("username", username).execute()
        return len(res.data) > 0


    def create_username(username):
        if not username or len(username.strip()) < 3:
            st.error("🚨 Username must be at least 3 characters.")
            return False

        username = username.strip()

        if username_exists(username):
            st.error("❌ Username already exists. Choose another one.")
            return False

        supabase.table("users").insert({"username": username}).execute()

        supabase.table("users_progress").upsert({
            "username": username,
            "progress": {
                "ratings": {},
                "attempts": {},
                "review_data": {},
                "timestamp": time.time(),
            }
        }).execute()

        st.success(f"🎉 Username '{username}' created!")
        return True


    def save_progress(username):
        export_data = {
            "ratings": st.session_state.get("ratings", {}),
            "attempts": st.session_state.get("attempts", {}),
            "review_data": st.session_state.get("review_data", {}),
            "timestamp": time.time(),
        }

        supabase.table("users_progress").upsert({
            "username": username,
            "progress": export_data
        }).execute()

        st.success("✔ Fortschritt gespeichert!")


    def load_progress(username):
        res = supabase.table("users_progress") \
            .select("progress") \
            .eq("username", username) \
            .limit(1) \
            .execute()

        if res.data:
            progress = res.data[0]["progress"]

            st.session_state["ratings"] = progress.get("ratings", {})
            st.session_state["attempts"] = progress.get("attempts", {})
            st.session_state["review_data"] = progress.get("review_data", {})

            st.success("✔ Fortschritt geladen! (Lokale Daten vollständig ersetzt)")
        else:
            st.warning("⚠ Kein Fortschritt für diesen Username gefunden.")


    # ============================================================
    # PATCHED pick_next_task (uses qid_original instead of id)
    # ============================================================

    def pick_next_task(tasks_subset):
        now = time.time()
        due_tasks = []

        for task in tasks_subset:
            qid = int(task["qid_original"])
            data = st.session_state["review_data"].get(qid, {"interval": 0.5, "last_review": 0})
            last_seen = data["last_review"]
            interval_seconds = data["interval"] * 86400

            if now - last_seen >= interval_seconds:
                due_tasks.append(task)

        if not due_tasks:
            due_tasks = sorted(tasks_subset, key=lambda t:
                st.session_state["review_data"].get(int(t["qid_original"]), {}).get("last_review", 0)
            )

        return random.choice(due_tasks)


    # ============================================================
    # Sidebar Login UI
    # ============================================================

    st.sidebar.header("🔐 Login / Cloud-Speicher")

    new_user = st.sidebar.text_input("Create Username", key="create_username_box")

    if st.sidebar.button("➡️ Create Username"):
        create_username(new_user)

    st.sidebar.caption("ℹ️ Einen beliebigen Nutzernamen anlegen, um deinen Lernfortschritt zu speichern.")

    st.sidebar.markdown("---")

    username = st.sidebar.text_input("Enter Username", key="login_username")

    st.sidebar.caption("ℹ️ Bereits erstellten Nutzernamen eingeben, um Fortschritt zu laden.")

    if st.sidebar.button("⬆ Load Progress from Previous"):
        if username:
            load_progress(username)
        else:
            st.error("Bitte Username eingeben.")

    if st.sidebar.button("⬇ Save/Upload Progress for Later"):
        if username:
            save_progress(username)
        else:
            st.error("Bitte Username eingeben.")

    # ============================================================
    # Display current task (PATCHED)
    # ============================================================

    task = get_task()
    qid = int(task["qid_original"])

    st.title(f"🧠 Task {qid} / {len(tasks)}")   # <-- replaces task['id']

    st.markdown(f"**🧩 QID:** `{qid}`")
    st.markdown(f"**📚 Category:** *{task['category']}*")
    st.markdown(f"### 📝 {task.get('question_raw', task.get('question'))}")


    # ============================================================
    # FILTER MODE (PATCHED FOR QID)
    # ============================================================

    filter_mode = st.radio(
        "Filtermodus wählen:",
        ["Alle Aufgaben", "Nach Kategorie", "Direkte QID"],
        horizontal=True
    )

    if st.session_state["prev_filter_mode"] != filter_mode:
        st.session_state["filter_changed"] = True
    st.session_state["prev_filter_mode"] = filter_mode

    filtered_tasks = tasks

    if filter_mode == "Nach Kategorie":
        all_categories = sorted({t["category"] for t in tasks})
        selected_cat = st.selectbox("Kategorie wählen:", all_categories)

        if st.session_state["prev_cat"] != selected_cat:
            st.session_state["filter_changed"] = True
        st.session_state["prev_cat"] = selected_cat

        filtered_tasks = [t for t in tasks if t["category"] == selected_cat]

    elif filter_mode == "Direkte QID":
        all_qids = sorted([int(t["qid_original"]) for t in tasks])

        selected_qid = st.number_input(
            "QID wählen:",
            min_value=min(all_qids),
            max_value=max(all_qids),
            step=1
        )

        if st.session_state["prev_qid"] != selected_qid:
            st.session_state["filter_changed"] = True
        st.session_state["prev_qid"] = selected_qid

        filtered_tasks = [qid_to_task[selected_qid]]


    # ============================================================
    # AUTO-NEXT ON FILTER CHANGE (PATCHED)
    # ============================================================

    if st.session_state.get("filter_changed", False):
        st.session_state["filter_changed"] = False

        next_t = pick_next_task(filtered_tasks)
        st.session_state["task_index"] = next_t["_index"]

        st.rerun()


    # ============================================================
    # Code editor and Run logic unchanged
    # ============================================================

    run_trigger = st.button("___run_hidden___", key="run_hidden", help="", type="secondary")

    st.markdown("""
    <style>
    button[data-testid="baseButton-secondary"]:has(span:contains("___run_hidden___")) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # JS for Ctrl+Enter
    st.markdown("""
    <script>
    document.addEventListener("keydown", function(e) {
        if (e.ctrlKey && e.key === "Enter") {
            const btn = window.parent.document.querySelector('button[k="run_hidden"]');
            if(btn){ btn.click(); }
        }
    });
    </script>
    """, unsafe_allow_html=True)

    # code editor
    content = st_ace(
        value="# Write your code below:\n\n",
        language="python",
        theme="dracula",
        key=f"ace_editor_{qid}",
        height=200,
    )


    # ============================================================
    # "Next Task" button PATCHED
    # ============================================================

    col1, col2, col3, col4 = st.columns(4)

    pressed_hard = col1.button("😤 Schwer", key=f"hard_btn_{qid}")
    pressed_medium = col2.button("🙂 Mittel", key=f"medium_btn_{qid}")
    pressed_easy = col3.button("😎 Einfach", key=f"easy_btn_{qid}")
    next_task = col4.button("➡️ Nächste Aufgabe")

    # rating storage
    if pressed_hard:
        st.session_state["last_rating"] = ("hard", qid)
    if pressed_medium:
        st.session_state["last_rating"] = ("medium", qid)
    if pressed_easy:
        st.session_state["last_rating"] = ("easy", qid)

    if "last_rating" in st.session_state:
        rating, rid = st.session_state["last_rating"]

        st.session_state["attempts"][rid] = st.session_state["attempts"].get(rid, 0) + 1
        st.session_state["ratings"][rid] = rating


        def update_review(task_id, difficulty):
            data = st.session_state["review_data"].get(task_id, {"interval": 0.5, "last_review": time.time()})
            interval = data["interval"]

            if difficulty == "hard":
                interval = max(interval * 0.5, 0.5)
            elif difficulty == "medium":
                interval = interval * 1.5
            elif difficulty == "easy":
                interval = interval * 2.5

            st.session_state["review_data"][task_id] = {
                "interval": interval,
                "last_review": time.time(),
            }


        update_review(rid, rating)

        if rating == "hard":
            st.warning(f"🔴 HARD — attempts now {st.session_state['attempts'][rid]}")
        elif rating == "medium":
            st.info(f"🟡 MEDIUM — attempts now {st.session_state['attempts'][rid]}")
        else:
            st.success(f"🟢 EASY — attempts now {st.session_state['attempts'][rid]}")

        if username:
            save_progress(username)

        del st.session_state["last_rating"]

    # actual navigation
    if next_task:
        next_t = pick_next_task(tasks)
        st.session_state["task_index"] = next_t["_index"]
        st.rerun()


    # progress bar
    progress = (st.session_state["task_index"] + 1) / len(tasks)
    st.progress(progress)
    st.caption(f"Task Index: {st.session_state['task_index']+1} / {len(tasks)}")


# ============================================================
# ❗ TAB 2: Issue melden (unchanged)
# ============================================================

# ... (unchanged code for Issue tab)


# ============================================================
# 📊 TAB 3: Progress Dashboard (unchanged except using qid)
# ============================================================

with tabs[2]:
    st.header("📊 Progress Dashboard")

    attempts_raw = st.session_state.get("attempts", {})

    if isinstance(attempts_raw, dict):
        attempts = {int(k): v for k, v in attempts_raw.items()}
    else:
        attempts = {}

    total_tasks = len(tasks)
    answered_once = sum(1 for qid, c in attempts.items() if c >= 1)

    st.subheader("🧮 Overview")
    st.write(f"**Total Tasks:** {total_tasks}")
    st.write(f"**Tasks answered at least once:** {answered_once}")

    st.progress(answered_once / total_tasks if total_tasks else 0)

    st.markdown("---")

    st.subheader("📋 Detailed Attempts per QID")

    if attempts:
        for qid, count in sorted(attempts.items()):
            st.write(f"• **QID {qid}** → {count}× durchgeführt")
    else:
        st.info("Noch keine Aufgaben beantwortet.")
