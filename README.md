# Active Recall App

## 1. Short Project Summary
ActiveRecallApp is a Streamlit-based practice environment for Python recall questions with an embedded editor and immediate feedback.  
It targets learning and retention by combining active recall prompts with a spaced-repetition interval that adapts to difficulty ratings.  
Users answer questions, run code, and optionally check results against expected outputs or variable values.  
Progress (attempt counts, ratings, review intervals) is tracked in session state and can be persisted to Supabase per username.  
The system outputs per-task feedback, progress dashboards, and updated scheduling metadata for future reviews.  
Issue reporting is supported via GitHub Gist uploads for task-level feedback.  

## 2. Technical Overview
**Task representation.** Each task is a JSON entry with an `id`, category, prompt text, expected values, solution code, and optional output checks. The app loads this file at startup and uses it as the authoritative task bank. 【F:app/tasks.json†L1-L40】【F:app/streamlit_app.py†L18-L32】

**User interaction and recall loop.** A user selects or is assigned a task, writes Python in a code editor, executes it, and optionally runs checks against expected values. The app captures stdout/stderr and renders success/failure feedback per variable or output. 【F:app/streamlit_app.py†L272-L519】

**Progress tracking and scoring logic.** Each completion is rated as hard/medium/easy, incrementing an attempt counter and storing the rating per task. This state drives a progress dashboard with totals and per-category completion percentages. 【F:app/streamlit_app.py†L551-L724】

**Scheduling / repetition logic.** Review scheduling is rule-based: a per-task interval (in days) is multiplied based on difficulty (0.5×, 1.5×, 2.5×) and compared to elapsed time to determine whether a task is due. Tasks are picked from the due set (or least-recently reviewed fallback) with random selection. 【F:app/streamlit_app.py†L134-L214】

**Storage and persistence.** User progress can be stored in Supabase under a username; local session state is merged with any existing remote record. Issue reports are uploaded as secret GitHub Gists. 【F:app/streamlit_app.py†L35-L133】【F:app/streamlit_app.py†L140-L182】

**ML vs. rule-based.** The system is rule-based. There is no trained model; scheduling is based on fixed interval multipliers and task selection is deterministic/random based on due time. This keeps behavior transparent and easy to audit. 【F:app/streamlit_app.py†L134-L214】

## 3. Folder Structure (Core Section)
```
ActiveRecallApp/
├── app/
│   ├── streamlit_app.py
│   ├── tasks.json
│   ├── extracted_solutions.txt
│   └── Check.py
├── data/
├── quarto/
└── requirements.txt
```

**Folder responsibilities**
- **`app/` (core logic & UI):** Streamlit interface, task execution/checking, scheduling logic, and Supabase/Gist integrations live in `streamlit_app.py`. Task content and answers live in `tasks.json`, while `extracted_solutions.txt` and `Check.py` are utility assets for task management. 【F:app/streamlit_app.py†L1-L724】【F:app/tasks.json†L1-L40】【F:app/extracted_solutions.txt†L1-L16】【F:app/Check.py†L1-L40】
- **`data/` (data storage):** CSV datasets used as learning materials or references for tasks. 【F:data/avocado.csv†L1-L3】
- **`quarto/` (reference docs):** Quarto notebooks and HTML references for formulas or Python syntax. 【F:quarto/formulas.qmd†L1-L20】
- **`requirements.txt` (dependencies):** Python package requirements for running the Streamlit app and integrations. 【F:requirements.txt†L1-L8】

**Data flow (input → recall → evaluation → storage)**
1. **Input:** Tasks are loaded from `app/tasks.json`, and a user selects a task via filtering or random due selection. 【F:app/tasks.json†L1-L40】【F:app/streamlit_app.py†L221-L360】
2. **Recall:** The user writes and runs code in the embedded editor; output is captured. 【F:app/streamlit_app.py†L352-L463】
3. **Evaluation:** Checks compare user variables/output to expected values and display feedback. 【F:app/streamlit_app.py†L464-L539】
4. **Storage:** Ratings and attempts update spaced-repetition intervals; progress is stored in session state and can be persisted to Supabase. 【F:app/streamlit_app.py†L551-L624】

**Location of key concerns**
- **Core logic:** `app/streamlit_app.py` (task loading, execution, checking, scheduling). 【F:app/streamlit_app.py†L18-L539】
- **UI:** `app/streamlit_app.py` (Streamlit tabs, editor, dashboards). 【F:app/streamlit_app.py†L36-L724】
- **Data storage:** `app/tasks.json` (task bank) and Supabase records via `users_progress`. 【F:app/tasks.json†L1-L40】【F:app/streamlit_app.py†L62-L133】
- **Experimentation/extensions:** `data/` and `quarto/` for reference datasets and supporting docs. 【F:data/avocado.csv†L1-L3】【F:quarto/formulas.qmd†L1-L20】

## 4. Engineering & Design Decisions
- **Rule-based scheduling:** The interval multiplier approach is simple, transparent, and easy to tune without requiring a model or training data. This matches the app’s learning focus and reduces operational complexity. 【F:app/streamlit_app.py†L134-L214】
- **Modularity via JSON task bank:** Tasks are externalized to `tasks.json`, enabling new questions or categories without changing code. 【F:app/tasks.json†L1-L40】【F:app/streamlit_app.py†L18-L32】
- **Immediate feedback loop:** Running and checking code in the same UI supports rapid iteration and reinforces recall. 【F:app/streamlit_app.py†L352-L539】
- **Simplicity vs. extensibility:** The app uses session state and lightweight persistence through Supabase instead of a dedicated backend, which keeps setup minimal but limits offline persistence and multi-device sync without credentials. 【F:app/streamlit_app.py†L35-L133】【F:app/streamlit_app.py†L551-L624】
- **Known limitations:** Executing arbitrary user code via `exec` is inherently unsafe outside controlled environments; scheduling does not consider user performance beyond difficulty labels; analytics are basic (attempt counts and category completion). 【F:app/streamlit_app.py†L392-L539】【F:app/streamlit_app.py†L551-L724】

## 5. What This Project Demonstrates
- **Technical skills:** Streamlit UI development, JSON-driven content pipelines, rule-based scheduling, and cloud persistence using Supabase and GitHub APIs. 【F:app/streamlit_app.py†L1-L724】
- **Software design vs. logic:** UI flow, persistence, and dashboarding reflect software design decisions; scheduling, checking logic, and interval updates reflect algorithmic logic. 【F:app/streamlit_app.py†L134-L724】
- **Role relevance:** Suitable for roles involving educational tooling, data/ML-adjacent product features, or applied analytics where transparent heuristics are preferred over opaque models. 【F:app/streamlit_app.py†L134-L724】
