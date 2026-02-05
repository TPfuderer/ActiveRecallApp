# ============================================================
# 🧠 Mini Python Playground – Spaced Repetition + Difficulty + Counter
# ============================================================
import pandas as pd
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
st.set_page_config(page_title="Python Exam Preparer", page_icon="💻", layout="centered")


# --- #Load tasks from JSON ---
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
    # --- Session state initialization ---
    if "task_index" not in st.session_state:
        # 🎲 beim allerersten Laden: zufälligen Task auswählen
        st.session_state["task_index"] = random.choice([t["id"] for t in tasks]) - 1

    if "ratings" not in st.session_state:
        st.session_state["ratings"] = {}
    if "attempts" not in st.session_state:
        st.session_state["attempts"] = {}
    if "review_data" not in st.session_state:
        st.session_state["review_data"] = {}

    # Track filter changes
    if "filter_changed" not in st.session_state:
        st.session_state["filter_changed"] = False
    if "prev_filter_mode" not in st.session_state:
        st.session_state["prev_filter_mode"] = None
    if "prev_cat" not in st.session_state:
        st.session_state["prev_cat"] = None
    if "prev_id" not in st.session_state:
        st.session_state["prev_id"] = None


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
        # 🔹 bestehenden Progress aus DB laden (falls vorhanden)
        res = supabase.table("users_progress") \
            .select("progress") \
            .eq("username", username) \
            .limit(1) \
            .execute()

        db_progress = res.data[0]["progress"] if res.data else {}

        # 🔹 lokaler Export (wie vorher)
        export_data = {
            "ratings": st.session_state.get("ratings", {}),
            "attempts": st.session_state.get("attempts", {}),
            "review_data": st.session_state.get("review_data", {}),
            "timestamp": time.time(),
        }

        # 🔹 MINIMALER Merge (DB + lokal)
        merged_progress = {
            "ratings": {**db_progress.get("ratings", {}), **export_data["ratings"]},
            "attempts": {**db_progress.get("attempts", {}), **export_data["attempts"]},
            "review_data": {**db_progress.get("review_data", {}), **export_data["review_data"]},
            "timestamp": export_data["timestamp"],
        }

        # 🔹 speichern wie vorher
        supabase.table("users_progress").upsert({
            "username": username,
            "progress": merged_progress
        }).execute()

        # 🔹 UX bleibt identisch
        st.success("✔ Fortschritt gespeichert!")


    def load_progress(username):
        res = supabase.table("users_progress") \
            .select("progress") \
            .eq("username", username) \
            .limit(1) \
            .execute()

        if res.data:
            progress = res.data[0]["progress"]

            # 1) Session-State HARD RESET (aber core keys intakt lassen)
            st.session_state["ratings"] = progress.get("ratings", {})
            st.session_state["attempts"] = progress.get("attempts", {})
            st.session_state["review_data"] = progress.get("review_data", {})

            st.success("✔ Fortschritt geladen! (Lokale Daten vollständig ersetzt)")
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

    # --- Current task ---
    task = get_task()
    tid = task["id"]

    # --- Display Header ---F
    st.title(f"🧠 Task {task['id']}/{len(tasks)}")

    from datetime import date

    exam_date = date(2026, 2, 12)
    days_left = (exam_date - date.today()).days

    if days_left >= 0:
        st.info(f"⏳ **Prüfung in {days_left} Tagen ** (12. Februar)")
    else:
        st.success("🎉 Prüfung vorbei – stark durchgezogen!")

    # 🔹 Show original QID
    if "qid_original" in task:
        st.markdown(f"**Original ID:** `{task['qid_original']}`")

    # 🔹 Show category
    if "category" in task:
        st.markdown(f"**Category:** *{task['category']}*")

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

    # detect filter mode change
    if st.session_state["prev_filter_mode"] != filter_mode:
        st.session_state["filter_changed"] = True
    st.session_state["prev_filter_mode"] = filter_mode

    filtered_tasks = tasks

    if filter_mode == "Nach Kategorie":
        all_categories = sorted({t["category"] for t in tasks})
        selected_cat = st.selectbox("Kategorie wählen:", all_categories)

        # detect category change
        if st.session_state["prev_cat"] != selected_cat:
            st.session_state["filter_changed"] = True
        st.session_state["prev_cat"] = selected_cat

        filtered_tasks = [t for t in tasks if t["category"] == selected_cat]

    elif filter_mode == "Direkte Task-ID":
        all_ids = [t["id"] for t in tasks]
        selected_id = st.number_input("Task-ID wählen:", min_value=min(all_ids), max_value=max(all_ids), step=1)

        # detect ID change
        if st.session_state["prev_id"] != selected_id:
            st.session_state["filter_changed"] = True
        st.session_state["prev_id"] = selected_id

        filtered_tasks = [t for t in tasks if t["id"] == selected_id]

    # AUTO-NEXT if filter changed
    if st.session_state.get("filter_changed", False):
        # Reset toggle BEFORE rerun (wichtig!)
        st.session_state["filter_changed"] = False

        # Pick next task
        next_t = pick_next_task(filtered_tasks)
        st.session_state["task_index"] = next_t["id"] - 1

        # Use new safe rerun method
        st.rerun()

    with st.popover("ℹ️ Filter-Hilfe"):
        st.markdown(
            """
            **Alle Aufgaben**  
            → Freies Lernen ohne Einschränkungen. Die App wählt automatisch fällige Aufgaben
            basierend auf deinem Wiederholungsintervall.

            **Nach Kategorie**  
            → Fokussiertes Lernen zu einem Themenbereich  
            (z. B. Listen, Dictionaries, Pandas, NumPy).

            **Direkte Task-ID**  
            → Ermöglicht **chronologisches Vorgehen** oder das gezielte Aufrufen
            einer bestimmten Aufgabe (z. B. nach Empfehlung oder zum Wiederholen).
            """
        )

    # --- Ctrl+Enter triggers hidden run button ---
    run_trigger = st.button("___run_hidden___", key="run_hidden", help="", type="secondary")

    # Hide the hidden button visually
    st.markdown("""
    <script>
    function hideRunHiddenButton() {
        document.querySelectorAll('div[data-testid="stButton"]').forEach(wrapper => {
            const text = wrapper.innerText?.trim();
            if (text === "run_hidden") {
                wrapper.style.display = "none";
            }
        });
    }

    // run once
    hideRunHiddenButton();

    // run again after Streamlit rerenders
    setTimeout(hideRunHiddenButton, 50);
    setTimeout(hideRunHiddenButton, 150);
    </script>
    """, unsafe_allow_html=True)

    # JS: Ctrl+Enter triggers the hidden button
    st.markdown("""
    <style>
    /* Hide the whole Streamlit button that contains 'run_hidden' */
    div[data-testid="stButton"]:has(strong:contains("run_hidden")) {
        display: none !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # --- Code editor ---
    content = st_ace(
        value="# Write your code below:\n\n",
        language="python",
        theme="dracula",
        key=f"ace_editor_{task['id']}",
        height=200,
    )


    # ============================
    # 🧠 Shared sandbox setup
    # ============================
    def build_user_globals():
        import numpy as np
        import pandas as pd
        import matplotlib.pyplot as plt
        import seaborn as sns
        import scipy
        import scipy.stats as stats
        import streamlit as st
        import sys
        import re
        import statsmodels.api as sm

        # 👉 ADD THESE
        from sklearn.model_selection import train_test_split
        from sklearn.linear_model import LinearRegression
        from sklearn.metrics import mean_squared_error, r2_score

        SAFE_BUILTINS = {
            "__build_class__": __build_class__,
            "__import__": __import__,
            "super": super,
            "StopIteration": StopIteration,

            # math / numeric helpers
            "pow": pow,
            "divmod": divmod,

            "sm": sm,

            # functional
            "map": map,
            "filter": filter,

            # iteration / slicing
            "reversed": reversed,

            # comparisons / identity
            "hash": hash,

            # exceptions commonly raised by user code
            "IndexError": IndexError,
            "KeyError": KeyError,
            "AttributeError": AttributeError,
            "ImportError": ImportError,
            "RuntimeError": RuntimeError,

            # casting / inspection
            "callable": callable,
            "id": id,

            # context helpers (harmless, often used)
            "object": object,

            # core
            "print": print,
            "open": open,
            "range": range,
            "len": len,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
            "round": round,
            "sorted": sorted,
            "enumerate": enumerate,
            "zip": zip,

            # logic / typing
            "any": any,
            "all": all,
            "bool": bool,
            "type": type,
            "isinstance": isinstance,

            # data types
            "int": int,
            "float": float,
            "str": str,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,

            # decorators
            "classmethod": classmethod,
            "staticmethod": staticmethod,
            "property": property,

            # exceptions
            "AssertionError": AssertionError,
            "ValueError": ValueError,
            "TypeError": TypeError,
            "ZeroDivisionError": ZeroDivisionError,
            "Exception": Exception,
            "FileNotFoundError": FileNotFoundError,
        }

        return {
            "__builtins__": SAFE_BUILTINS,
            "__name__": "__main__",

            # scientific stack
            "np": np,
            "pd": pd,
            "plt": plt,
            "sns": sns,
            "scipy": scipy,
            "stats": stats,

            # 👉 ADD THESE
            "train_test_split": train_test_split,
            "LinearRegression": LinearRegression,
            "mean_squared_error": mean_squared_error,
            "r2_score": r2_score,

            # infra
            "st": st,
            "sys": sys,
            "re": re,
        }


    # ============================
    # ▶️ Run without Check
    # ============================
    do_run = st.button("▶️ Run without Check") or run_trigger

    if do_run:
        st.subheader("🖥️ Execution Result")

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                user_globals = build_user_globals()
                exec(content, user_globals)

            output = stdout_buffer.getvalue().strip()
            errors = stderr_buffer.getvalue().strip()

            if output:
                st.text_area("📤 Output", output, height=150)
            if errors:
                st.error(errors)
            if not output and not errors:
                st.info("ℹ️ No output shown — `print()` is required.")

        except Exception as e:
            st.error(f"❌ Exception during execution:\n{e}")

    # ============================
    # ▶️ Run & Check
    # ============================
    if st.button("▶️ Run & Check"):
        st.subheader("🖥️ Execution Result")

        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout_buffer), contextlib.redirect_stderr(stderr_buffer):
                user_globals = build_user_globals()
                exec(content, user_globals)

            output = stdout_buffer.getvalue()
            errors = stderr_buffer.getvalue()

            if output.strip():
                st.text_area("🖨️ Output", output, height=120)
            if errors.strip():
                st.error(errors)

            # ============================
            # Checking logic (UNCHANGED)
            # ============================

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

                    ALLOWED_TYPES = (list, set, dict, tuple)

                    if isinstance(user_val, ALLOWED_TYPES) and isinstance(exp, ALLOWED_TYPES):
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

            if expected_output is not None:
                if output == expected_output:
                    results.append("✅ Printed output is correct.")
                else:
                    results.append(
                        f"❌ Printed output was `{output.strip()}` "
                        f"(expected `{expected_output.strip()}`)"
                    )

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
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        pressed_hard = st.button("😤 Schwer", key=f"hard_btn_{tid}")

    with col2:
        pressed_medium = st.button("🙂 Mittel", key=f"medium_btn_{tid}")

    with col3:
        pressed_easy = st.button("😎 Einfach", key=f"easy_btn_{tid}")

    with col4:
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

        # 1) Attempt Counter aktualisieren
        st.session_state["attempts"][rid] = st.session_state["attempts"].get(rid, 0) + 1

        # 2) Rating speichern
        st.session_state["ratings"][rid] = rating

        # 3) Spaced Repetition Interval aktualisieren
        update_review(rid, rating)

        # 4) Feedback anzeigen
        if rating == "hard":
            st.warning(f"🔴 Successfully counted as HARD — attempts now: {st.session_state['attempts'][rid]}")
        elif rating == "medium":
            st.info(f"🟡 Successfully counted as MEDIUM — attempts now: {st.session_state['attempts'][rid]}")
        elif rating == "easy":
            st.success(f"🟢 Successfully counted as EASY — attempts now: {st.session_state['attempts'][rid]}")

        # 🆕 5) 🔥 Automatisch Supabase speichern (existierende Funktion!)
        if username:
            save_progress(username)
            st.toast("💾 Fortschritt automatisch gespeichert!")

        # 6) Event löschen, damit es nicht doppelt abgefeuert wird
        del st.session_state["last_rating"]

    # -------------------------------------------------------
    # 💡 Lösung & Erklärung (immer sichtbar, aber eingeklappt)
    # -------------------------------------------------------
    with st.expander("💡 Lösung & Erklärung", expanded=False):
        st.code(task["solution_code"], language="python")
        st.markdown(task.get("explanation", "_Keine Erklärung für diese Aufgabe hinterlegt._"))

    with st.popover("ℹ️"):
        st.write(
            """
            **So funktionieren die Buttons:**

            • **Schwer / Mittel / Einfach** → bestimmt das Intervall für die Wiederholung  
            • Beim Klicken speichert die App **automatisch deinen Lernfortschritt**  
            • Speicherung funktioniert **nur**, wenn ein **Nutzername existiert UND eingegeben ist**  
            • **Next** → lädt direkt die nächste Aufgabe
            """
        )

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

    # =======================================================
    # 📊 Progress Dashboard (RENDERED)
    # =======================================================
    st.header("📊 Progress Dashboard")

    # --- Attempts sicher normalisieren ---
    attempts_raw = st.session_state.get("attempts", {})

    # attempts kann None, list, str, usw. sein → IMMER in dict casten!
    if isinstance(attempts_raw, dict):
        attempts = {int(k): v for k, v in attempts_raw.items()}
    else:
        attempts = {}

    total_tasks = len(tasks)
    answered_once = sum(1 for c in attempts.values() if c >= 1)

    # --- Overview ---
    st.subheader("🧮 Overview")
    st.write(f"**Total Tasks:** {total_tasks}")
    st.write(f"**Tasks answered at least once:** {answered_once}")
    st.progress(answered_once / total_tasks if total_tasks else 0)

    st.markdown("---")

    # ============================================================
    # 📊 Progress per Category (% completed)
    # ============================================================

    import pandas as pd
    import altair as alt

    # -----------------------------
    # 1️⃣ Attempts normalisieren
    # -----------------------------
    attempts_raw = st.session_state.get("attempts", {})
    attempts = {int(k): v for k, v in attempts_raw.items()} if isinstance(attempts_raw, dict) else {}

    # -----------------------------
    # 2️⃣ Tasks → DataFrame
    # -----------------------------
    df = pd.DataFrame(tasks)[["id", "category"]].copy()

    df["answered"] = df["id"].apply(lambda tid: 1 if attempts.get(tid, 0) >= 1 else 0)

    # -----------------------------
    # 3️⃣ Aggregation pro Kategorie
    # -----------------------------
    cat_df = (
        df.groupby("category")
        .agg(
            answered=("answered", "sum"),
            total=("answered", "count")
        )
        .reset_index()
    )

    cat_df["pct"] = (cat_df["answered"] / cat_df["total"] * 100).round(1)


    # -----------------------------
    # 4️⃣ Schöne kompakte Labels
    # -----------------------------
    def format_category_label(cat):
        main = cat.split("(")[0].strip()
        parts = main.split(" - ")

        if len(parts) == 2:
            return f"{parts[0]} – {parts[1]}"
        else:
            return main


    cat_df["category_label"] = cat_df["category"].apply(format_category_label)

    # -----------------------------
    # 5️⃣ Sortierung: höchster Fortschritt zuerst
    # -----------------------------
    cat_df = cat_df.sort_values(
        by=["pct", "answered", "total"],
        ascending=[False, False, False]
    )

    # -----------------------------
    # 6️⃣ Horizontaler Prozent-Balken
    # -----------------------------
    st.subheader("📊 Fortschritt pro Kategorie (%)")
    st.caption("Mindestens Einmal Beantwortet")

    chart = (
        alt.Chart(cat_df)
        .mark_bar(color="#27ae60")
        .encode(
            y=alt.Y(
                "category_label:N",
                sort=cat_df["category_label"].tolist(),
                title="Kategorie",
                axis=alt.Axis(
                    labelLimit=0,  # nichts abschneiden
                    labelAlign="right",  # Text zeigt nach links
                    labelPadding=6,
                    offset=5  # 🔥 DAS verschiebt die Balken nach rechts
                )
            ),
            x=alt.X(
                "pct:Q",
                scale=alt.Scale(domain=[0, 100]),
                title="Abgeschlossene Aufgaben (%)"
            ),
            tooltip=[
                alt.Tooltip("category:N", title="Kategorie"),
                alt.Tooltip("total:Q", title="Gesamtfragen"),
                alt.Tooltip("answered:Q", title="Beantwortet"),
                alt.Tooltip("pct:Q", title="Fortschritt (%)")
            ]
        )
        .properties(
            height=36 * len(cat_df)
        )
    )

    st.altair_chart(chart, width="stretch")

# ============================================================
# ❗ TAB 2: Issue melden
# ============================================================
with tabs[1]:
    st.header("❗ Fehler / Issue melden")

    st.write(
        "Melde einen Fehler zu einer bestimmten Aufgabe **oder** ein "
        "allgemeines Problem. Danke für die Hilfe!"
    )

    # ------------------------------------------------------
    # OPTIONAL: Task ID
    # ------------------------------------------------------
    task_id_input = st.number_input(
        "Aufgaben-ID (optional):",
        min_value=0,
        step=1,
        help="0 lassen, wenn sich das Problem nicht auf eine spezifische Aufgabe bezieht."
    )

    # ------------------------------------------------------
    # PROBLEM TEXT
    # ------------------------------------------------------
    description = st.text_area(
        "📝 Fehlerbeschreibung:",
        placeholder="Beschreibe, was nicht funktioniert hat, was falsch war oder verbessert werden soll...",
        height=180
    )

    # ------------------------------------------------------
    # UPLOAD BUTTON
    # ------------------------------------------------------
    if st.button("Issue Absenden"):
        if not description.strip():
            st.error("Bitte eine Fehlerbeschreibung eingeben.")
            st.stop()

        # Gist Payload vorbereiten
        payload = {
            "task_id": int(task_id_input) if task_id_input > 0 else None,
            "description": description.strip()
        }

        # Upload durchführen (existierende Funktion)
        try:
            url = upload_issue_to_gist(task_id_input, payload)
            if url:
                st.success(f"🎉 Issue gespeichert!")
                #st.markdown(f"[🔗 Gist ansehen]({url})")
        except Exception as e:
            st.error(f"❌ Fehler beim Speichern: {e}")


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
