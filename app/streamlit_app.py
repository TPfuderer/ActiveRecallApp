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

    # --- Session state initialization ---
    if "task_index" not in st.session_state:
        st.session_state["task_index"] = 0
    if "ratings" not in st.session_state:
        st.session_state["ratings"] = {}
    if "attempts" not in st.session_state:
        st.session_state["attempts"] = {}
    if "review_data" not in st.session_state:
        st.session_state["review_data"] = {}

    # --- Helper functions ---
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

        # check existence
        if username_exists(username):
            st.error("❌ Username already exists. Choose another one.")
            return False

        # create user
        supabase.table("users").insert({"username": username}).execute()

        # create empty progress record
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

            st.session_state["ratings"].update(progress.get("ratings", {}))
            st.session_state["attempts"].update(progress.get("attempts", {}))
            st.session_state["review_data"].update(progress.get("review_data", {}))

            st.success("✔ Fortschritt geladen!")
        else:
            st.warning("⚠ Kein Fortschritt für diesen Username gefunden.")


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


    def upload_issue_to_gist(task_id, data):
        """Upload a single issue as a secret GitHub Gist."""
        token = st.secrets["GITHUB_TOKEN"]

        url = "https://api.github.com/gists"
        headers = {"Authorization": f"token {token}"}

        payload = {
            "files": {
                f"issue_task_{task_id}.json": {
                    "content": json.dumps(data, indent=2, ensure_ascii=False)
                }
            },
            "public": False  # secret gist
        }

        resp = requests.post(url, headers=headers, json=payload)

        if resp.status_code == 201:
            return resp.json()["html_url"]
        else:
            st.error(f"❌ Fehler beim Gist-Upload: {resp.text}")
            return None

    def pick_next_task(tasks):
        now = time.time()
        due_tasks = []

        for task in tasks:
            tid = task["id"]
            data = st.session_state["review_data"].get(tid, {"interval": 0.5, "last_review": 0})
            last_seen = data["last_review"]
            interval_seconds = data["interval"] * 86400

            if now - last_seen >= interval_seconds:
                due_tasks.append(task)

        if not due_tasks:
            due_tasks = sorted(tasks, key=lambda t: st.session_state["review_data"].get(t["id"], {}).get("last_review", 0))

        return random.choice(due_tasks)


    st.sidebar.header("🔐 Login / Cloud-Speicher")

    new_user = st.sidebar.text_input("Create Username", key="create_username_box")

    if st.sidebar.button("➡️ Create Username"):
        create_username(new_user)

    st.sidebar.markdown("---")

    username = st.sidebar.text_input("Enter Username", key="login_username")

    if st.sidebar.button("⬆ Load Progress"):
        if username:
            load_progress(username)
        else:
            st.error("Bitte Username eingeben.")

    if st.sidebar.button("⬇ Save Progress"):
        if username:
            save_progress(username)
        else:
            st.error("Bitte Username eingeben.")

    # --- Current task ---
    task = get_task()
    tid = task["id"]

    # --- Display Header ---F
    st.title(f"🧠 Task {task['id']}/{len(tasks)}")

    # 🔹 Show original QID
    if "qid_original" in task:
        st.markdown(f"**🧩 Original ID:** `{task['qid_original']}`")

    # 🔹 Show category
    if "category" in task:
        st.markdown(f"**📚 Category:** *{task['category']}*")

    # 🔹 Show question
    st.markdown(f"### 📝 {task.get('question_raw', task.get('question'))}")

    # ----------------------------------------
    # 🔽 FILTER: Task-ID oder Kategorie
    # ----------------------------------------

    filter_mode = st.radio(
        "Filtermodus wählen:",
        ["Alle Aufgaben", "Nach Kategorie", "Direkte Task-ID"],
        horizontal=True
    )

    filtered_tasks = tasks

    if filter_mode == "Nach Kategorie":
        all_categories = sorted({t["category"] for t in tasks})
        selected_cat = st.selectbox("Kategorie wählen:", all_categories)
        filtered_tasks = [t for t in tasks if t["category"] == selected_cat]

    elif filter_mode == "Direkte Task-ID":
        all_ids = [t["id"] for t in tasks]
        selected_id = st.number_input("Task-ID wählen:", min_value=min(all_ids), max_value=max(all_ids), step=1)
        filtered_tasks = [t for t in tasks if t["id"] == selected_id]

    # --- Ctrl+Enter triggers hidden run button ---
    run_trigger = st.button("___run_hidden___", key="run_hidden")

    # Hide the hidden button visually
    st.markdown("""
    <style>
    button[k="run_hidden"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # JS: Ctrl+Enter triggers the hidden button
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

    # --- Code editor ---
    content = st_ace(
        value="# Write your code below:\n\n",
        language="python",
        theme="dracula",
        key=f"ace_editor_{task['id']}",
        height=200,
    )

    # --- Unified run: manual button OR Ctrl+Enter ---
    do_run = st.button("▶️ Run") or run_trigger

    if do_run:
        st.subheader("🖥️ Execution Result")

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            # Execute user code
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                user_globals = {}
                exec(content, user_globals)

            # Output collection
            output = stdout_buffer.getvalue().strip()
            errors = stderr_buffer.getvalue().strip()

            if output:
                st.text_area("📤 Output", output, height=150)

            if errors:
                st.error(errors)

            if not output and not errors:
                st.info("ℹ️ Code executed without output.")

        except Exception as e:
            st.error(f"❌ Exception during execution:\n{e}")

    # ============================
    # ▶️ RUN & CHECK LOGIC
    # ============================

    if st.button("▶️ Run & Check"):
        st.subheader("🖥️ Execution Result")

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

            # Checking logic
            check_vars = task.get("check_variable", [])
            expected_vals = task.get("expected_value", [])
            expected_output = task.get("expected_output", None)
            results = []

            if isinstance(check_vars, list):
                for var, exp in zip(check_vars, expected_vals):
                    user_val = user_globals.get(var, None)

                    # --- tolerance-based check (JSON configurable) ---
                    check_type = task.get("check_type", "exact")
                    if check_type == "float_tolerance":
                        tol = task.get("tolerance", 0.001)
                        try:
                            if isinstance(user_val, (int, float)) and abs(user_val - exp) <= tol:
                                results.append(f"✅ `{var}` ≈ {user_val} (within ±{tol})")
                                continue
                        except:
                            pass
                    # --------------------------------------------------

                    # ============================
                    # 💡 TYPE-FLEXIBLE CHECK
                    #   akzeptiert list, set, dict, tuple
                    # ============================

                    ALLOWED_TYPES = (list, set, dict, tuple)

                    # Falls Nutzer andere Struktur liefert → Warnung
                    if isinstance(user_val, ALLOWED_TYPES) and isinstance(exp, ALLOWED_TYPES):
                        # Sets sortieren / normalisieren
                        if isinstance(user_val, set):
                            user_norm = sorted(user_val)
                        elif isinstance(user_val, dict):
                            user_norm = sorted(user_val.items())
                        else:
                            user_norm = user_val

                        if isinstance(exp, set):
                            exp_norm = sorted(exp)
                        elif isinstance(exp, dict):
                            exp_norm = sorted(exp.items())
                        else:
                            exp_norm = exp

                        if user_norm == exp_norm:
                            results.append(f"✅ `{var}` = {user_val}")
                        else:
                            results.append(f"❌ `{var}` = {user_val} (expected {exp})")

                    else:
                        # exact fallback (für ints, floats, strings, etc.)
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

            # Check printed output if defined
            if expected_output is not None:
                if output == expected_output:
                    results.append("✅ Printed output is correct.")
                else:
                    results.append(f"❌ Printed output was `{output.strip()}` (expected `{expected_output.strip()}`)")

            # Show results
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

    # --- Buttons (persistent) ---
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        show_answer = st.button("💡 Antwort anzeigen")

    with col2:
        pressed_hard = st.button("😤 Schwer", key=f"hard_btn_{tid}")

    with col3:
        pressed_medium = st.button("🙂 Mittel", key=f"medium_btn_{tid}")

    with col4:
        pressed_easy = st.button("😎 Einfach", key=f"easy_btn_{tid}")

    with col5:
        next_task = st.button("➡️ Nächste Aufgabe")

    # -------------------------------------------------------
    # 🔥 PERSISTENTES CLICK-EVENT FÜR RATINGS
    # -------------------------------------------------------

    # Button-Clicks speichern (nur 1 Frame)
    if pressed_hard:
        st.session_state["last_rating"] = ("hard", tid)

    if pressed_medium:
        st.session_state["last_rating"] = ("medium", tid)

    if pressed_easy:
        st.session_state["last_rating"] = ("easy", tid)

    # -------------------------------------------------------
    # 📌 WENN EIN RATING GESPEICHERT WURDE → VERARBEITEN
    # -------------------------------------------------------
    if "last_rating" in st.session_state:
        rating, rid = st.session_state["last_rating"]

        # Attempt Counter
        st.session_state["attempts"][rid] = st.session_state["attempts"].get(rid, 0) + 1

        # Rating speichern
        st.session_state["ratings"][rid] = rating

        # Spaced Repetition Interval aktualisieren
        update_review(rid, rating)

        # 🔔 Erfolgsmeldung anzeigen
        if rating == "hard":
            st.warning(f"🔴 Successfully counted as HARD — attempts now: {st.session_state['attempts'][rid]}")
        elif rating == "medium":
            st.info(f"🟡 Successfully counted as MEDIUM — attempts now: {st.session_state['attempts'][rid]}")
        elif rating == "easy":
            st.success(f"🟢 Successfully counted as EASY — attempts now: {st.session_state['attempts'][rid]}")

        # Event löschen, damit es nicht erneut triggered wird
        del st.session_state["last_rating"]

    # -------------------------------------------------------
    # SHOW ANSWER
    # -------------------------------------------------------
    if show_answer:
        with st.expander("💡 Lösung & Erklärung"):
            st.code(task["solution_code"], language="python")
            st.markdown(task["explanation"])

    # -------------------------------------------------------
    # NEXT TASK
    # -------------------------------------------------------
    if next_task:
        next_t = pick_next_task(filtered_tasks)
        st.session_state["task_index"] = next_t["id"] - 1
        st.success(f"🕒 Nächste Aufgabe: #{next_t['id']}")
        st.rerun()

    # --- Fortschritt ---
    progress = (st.session_state["task_index"] + 1) / len(tasks)
    st.progress(progress)
    st.caption(f"Aufgabe {st.session_state['task_index'] + 1} von {len(tasks)}")

    # --- Statistik ---
    if st.session_state["ratings"]:
        st.markdown("### 📊 Deine Bewertungen & Durchführungen:")

        # 🔥 IDs sicher in INT konvertieren (LÖST dein Problem!)
        normalized_ratings = {int(k): v for k, v in st.session_state["ratings"].items()}
        normalized_attempts = {int(k): v for k, v in st.session_state["attempts"].items()}
        normalized_review = {int(k): v for k, v in st.session_state["review_data"].items()}

        for tid in sorted(normalized_ratings.keys()):
            rating = normalized_ratings[tid]
            count = normalized_attempts.get(tid, 0)
            data = normalized_review.get(tid, {})
            interval = data.get("interval", 0)
            next_in = round(interval, 2)

            st.write(
                f"• Task {tid}: {rating.capitalize()} – {count}x durchgeführt | ⏳ ~{next_in} Tage"
            )


    # ============================================================
    # 📦 Fortschritt Export / Import
    # ============================================================

    st.markdown("## 📦 Fortschritt speichern / laden")

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

    uploaded = st.file_uploader("⬆️ JSON Fortschritt importieren", type="json")

    if "import_done" not in st.session_state:
        st.session_state["import_done"] = False

    if uploaded and not st.session_state["import_done"]:
        try:
            imported = json.load(uploaded)

            st.session_state["ratings"].update(imported.get("ratings", {}))
            st.session_state["attempts"].update(imported.get("attempts", {}))
            st.session_state["review_data"].update(imported.get("review_data", {}))

            st.session_state["import_done"] = True

            st.success("✅ Fortschritt erfolgreich importiert! Seite lädt neu…")
            st.rerun()

        except Exception as e:
            st.error(f"❌ Fehler beim Import: {e}")

# ============================================================
# ❗ TAB 2: Issue melden
# ============================================================
with tabs[1]:
    st.header("❗ Fehler / Issue melden")

    # issue_id kann auch 0 sein (bei Start)
    issue_id = st.number_input("Aufgaben-ID mit Fehler:", step=1, min_value=1)

    # Wenn keine ID eingegeben → Info anzeigen
    if issue_id == 0:
        st.info("Bitte eine gültige Aufgaben-ID eingeben.")
        st.stop()  # Tab 2 endet hier, Tab 3 lädt trotzdem
        # (st.stop() ist SAFE innerhalb eines Tabs!)

    # Wenn eine ID eingegeben wurde (>0)
    task = next((t for t in tasks if t["id"] == issue_id), None)

    if task is None:
        st.error("❌ Keine Aufgabe mit dieser ID gefunden.")
        st.stop()

    # ---- 1. Fixierter Teil ----
    st.subheader("🔒 Fixierte Felder (nicht editierbar)")
    fixed = {
        "id": task["id"],
        "question": task.get("question_raw", task.get("question"))
    }
    st.json(fixed)

    # ---- 2. Editierbarer JSON Teil ----
    st.subheader("✏️ Änderbarer JSON-Bereich")

    editable = {
        k: v for k, v in task.items()
        if k not in ["id", "question"]
    }

    editable_str = json.dumps(editable, indent=2, ensure_ascii=False)

    editable_input = st.text_area(
        "Bearbeite JSON:",
        value=editable_str,
        height=300
    )

    # ---- Gist Upload Button ----
    if st.button("💾 Issue als Gist speichern"):
        try:
            edited = json.loads(editable_input)
            url = upload_issue_to_gist(issue_id, edited)

            if url:
                st.success("🎉 Issue gespeichert!")
        except Exception as e:
            st.error(f"❌ JSON Fehler: {e}")

# ============================================================
# 📊 TAB 3: Progress Dashboard
# ============================================================
with tabs[2]:
    st.header("📊 Progress Dashboard")

    # --- Attempts sicher normalisieren ---
    attempts_raw = st.session_state.get("attempts", {})

    # attempts kann None, list, str, usw. sein → IMMER in dict casten!
    if isinstance(attempts_raw, dict):
        # Keys in int konvertieren
        attempts = {int(k): v for k, v in attempts_raw.items()}
    else:
        attempts = {}

    total_tasks = len(tasks)
    answered_once = sum(1 for t, c in attempts.items() if c >= 1)

    # --- Overview ---
    st.subheader("🧮 Overview")
    st.write(f"**Total Tasks:** {total_tasks}")
    st.write(f"**Tasks answered at least once:** {answered_once}")

    st.progress(answered_once / total_tasks if total_tasks else 0)

    st.markdown("---")

    # --- Detailed attempts ---
    st.subheader("📋 Detailed Attempts per Task")

    if attempts:
        for tid, count in sorted(attempts.items()):
            st.write(f"• **Task {tid}** → {count}× durchgeführt")
    else:
        st.info("Noch keine Aufgaben beantwortet.")
