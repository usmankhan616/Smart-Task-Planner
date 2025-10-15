# Smart Task Planner
<img width="1902" height="900" alt="Screenshot 2025-10-15 154047" src="[https://github.com/user-attachments/assets/b8838334-23cc-4a7f-bfd0-edc516fdc642](https://youtu.be/XkQks-2c0OE)" />
[![Watch the Demo](https://img.youtube.com/vi/XkQks-2c0OE/0.jpg)](https://youtu.be/XkQks-2c0OE)

https://youtu.be/XkQks-2c0OE

<img width="1897" height="897" alt="Screenshot 2025-10-15 154147" src="https://github.com/user-attachments/assets/3cee9952-7197-4fc7-8391-03af5eb916f0" />
<img width="1877" height="898" alt="Screenshot 2025-10-15 154233" src="https://github.com/user-attachments/assets/241035fc-9286-4be8-b87e-9d6f8f7d2b4a" />
<img width="1102" height="913" alt="Screenshot 2025-10-15 154322" src="https://github.com/user-attachments/assets/3dd14c47-215c-413b-baef-36b967137008" />
<img width="1101" height="918" alt="Screenshot 2025-10-15 154340" src="https://github.com/user-attachments/assets/b209a4aa-0e16-49e6-941b-eeb3c5f687ba" />



Break user goals into actionable tasks with timelines using AI reasoning. Users sign up/log in, submit a goal (e.g., "Launch a product in 2 weeks"), and receive a structured multi-step plan with dependencies, phases, priorities, and estimated durations. Plans and tasks are stored for later tracking in the Profile page.

## Key Features
- AI-powered task planning with multi-model reasoning
  - First model drafts task names
  - Second model elaborates each task (description, duration, dependencies, phase, priority)
  - Robust JSON parsing with fallback when providers fail
- Simple JWT cookie auth (login/signup)
- Persisted plans and tasks (SQLModel)
- Progress tracking (submit/unsubmit per task, overall submission percentage)
- Smooth UX: plan renders below the form first, then auto-navigates to Profile

## Architecture Overview
- FastAPI backend serving HTML (Jinja2) and JSON endpoints
- Templates with TailwindCSS and htmx for progressive, dynamic UX
- SQLModel ORM (Plan, Task, TaskProgress, User)
- Optional Celery + Redis (included scaffolding for background planning)
- LLM abstraction via LiteLLM supporting multiple providers (OpenAI, Anthropic, Gemini)

```
Flow: UI (htmx) -> FastAPI (/api/generate-plan) -> LLMService (multi-model) -> DB (SQLModel) -> render result -> redirect to /profile
```

## Tech Stack
- Backend: FastAPI, SQLModel, Pydantic/Dataclasses
- Auth/Security: python-jose (JWT), passlib[bcrypt]
- Templates/UI: Jinja2, TailwindCSS, htmx
- LLM: LiteLLM (providers: OpenAI, Anthropic, Google Gemini)
- Task queue (optional): Celery with Redis backend/broker
- Config: python-dotenv
- Database: Configurable via `DATABASE_URL` (SQLite/PostgreSQL/etc.)

## LLM Strategy (Reasoning and Diversity)
To avoid identical responses across tasks and goals:
- Stage 1 (Draft): A model generates 5–8 distinct task names for the goal
- Stage 2 (Elaborate): A second model expands each task name into a unique, detailed task spec
- Fallbacks: If any stage fails, single-shot planning or rule-based planning kicks in

Providers are auto-configured from available API keys and used with graceful fallback.

## Data Model (summary)
- User (email, hashed_password, relationships to plans)
- Plan (user_goal, created_at, owner)
- Task (taskName, description, duration, dependencies, phase, priority, status)
- TaskProgress (status, comment, timestamp, task)

Task status values are uppercase for consistency (e.g., `SUBMITTED`, `REJECTED`, `COMPLETED`).

## Endpoints
- GET `/` Home (goal input)
- POST `/api/generate-plan` Generate a plan and render it, then auto-redirect to `/profile`
- GET `/profile` View plans and progress
- POST `/api/submit-task/{task_id}` Toggle a task between submitted/not submitted
- POST `/api/toggle-task/{task_id}` Toggle a task between submitted/completed
- GET `/signup`, POST `/signup` Sign up
- GET `/login`, POST `/login` Log in
- GET `/logout` Log out

## Setup
1) Python dependencies

```bash path=null start=null
pip install fastapi uvicorn jinja2 python-multipart sqlmodel sqlalchemy python-dotenv
pip install passlib[bcrypt] python-jose[cryptography]
pip install litellm redis celery
# Optional provider SDKs (only if you call them directly): openai anthropic google-generativeai
```

2) Environment variables

```bash path=null start=null
# .env
DATABASE_URL=sqlite:///smart.db
# One or more of the following (any subset works)
OPENAI_API_KEY={{OPENAI_API_KEY}}
ANTHROPIC_API_KEY={{ANTHROPIC_API_KEY}}
GEMINI_API_KEY={{GEMINI_API_KEY}}
```

3) Run the web app

```bash path=null start=null
uvicorn app.main:app --reload
```

4) (Optional) Run Redis and Celery worker
- Ensure Redis is running locally (default `redis://localhost:6379/0`)

```bash path=null start=null
celery -A app.celery_config.celery_app worker -l info
```

Tables are created automatically on startup via SQLModel metadata.

## Usage
- Sign up or log in
- Enter a goal on the home page and click "Generate Plan"
- The generated plan renders below the button, then the app navigates to Profile
- In Profile, toggle submission status for tasks and see overall progress

## Project Structure (selected)
- `app/main.py` FastAPI routes, page rendering, plan generation flow
- `app/llm_service.py` Multi-model planning logic and fallbacks
- `app/models.py` SQLModel entities and enums
- `app/database.py` DB engine and table creation
- `app/security.py` Password hashing and JWT cookie auth
- `app/tasks.py`, `app/celery_config.py` Optional Celery + Redis integration
- `templates/*.html` Jinja2 templates using TailwindCSS and htmx

## Evaluation Mapping (Professor’s Requirements)
- Objective met: Goals are broken into actionable tasks with timelines and dependencies
- Backend API: `/api/generate-plan` processes input and generates plan
- Optional DB: Plans and tasks are stored via SQLModel
- LLM Reasoning: Multi-model workflow ensures richer, task-specific outputs
- Prompting: System and user prompts enforce JSON, phases, dependencies, deadlines
- Deliverables: Codebase + README; add a short demo video showing goal->plan->profile flow

## Notes
- If multiple LLM keys are present, the service will try them in order (with fallbacks)
- If no keys are configured, a rule-based planner provides a sensible default plan
- Status casing is unified to ensure UI progress reflects submissions correctly
