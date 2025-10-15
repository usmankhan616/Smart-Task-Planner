Of course\! Here is a more polished and attractive version of your README file. I've focused on improving the structure, readability, and visual appeal using standard Markdown formatting.

-----

\<div align="center"\>
\<h1\>Smart Task Planner\</h1\>
\<p\>
An intelligent planner that breaks down your ambitious goals into concrete, actionable steps using a multi-model AI approach.
\</p\>
\<p\>
\<img src="[https://img.shields.io/badge/Python-3776AB?style=for-the-badge\&logo=python\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/Python-3776AB%3Fstyle%3Dfor-the-badge%26logo%3Dpython%26logoColor%3Dwhite)" alt="Python"/\>
\<img src="[https://img.shields.io/badge/FastAPI-009688?style=for-the-badge\&logo=fastapi\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/FastAPI-009688%3Fstyle%3Dfor-the-badge%26logo%3Dfastapi%26logoColor%3Dwhite)" alt="FastAPI"/\>
\<img src="[https://img.shields.io/badge/HTMX-3366CC?style=for-the-badge\&logo=htmx\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/HTMX-3366CC%3Fstyle%3Dfor-the-badge%26logo%3Dhtmx%26logoColor%3Dwhite)" alt="HTMX"/\>
\<img src="[https://img.shields.io/badge/Tailwind\_CSS-38B2AC?style=for-the-badge\&logo=tailwind-css\&logoColor=white](https://www.google.com/search?q=https://img.shields.io/badge/Tailwind_CSS-38B2AC%3Fstyle%3Dfor-the-badge%26logo%3Dtailwind-css%26logoColor%3Dwhite)" alt="Tailwind CSS"/\>
\<img src="[https://img.shields.io/badge/SQLModel-007BFF?style=for-the-badge](https://www.google.com/search?q=https://img.shields.io/badge/SQLModel-007BFF%3Fstyle%3Dfor-the-badge)" alt="SQLModel"/\>
\</p\>
\</div\>

**Smart Task Planner** transforms your high-level goals into manageable, step-by-step project plans. Simply describe what you want to achieve—like "Launch a new website in 3 weeks"—and our AI-driven engine will generate a detailed roadmap complete with tasks, timelines, dependencies, and priorities. Track your progress, manage your plans, and turn your vision into reality.

\<details\>
\<summary\>\<strong\>✨ View Gallery\</strong\>\</summary\>
<br>
\<p align="center"\>
\<img width="800" alt="Generated Plan" src="[https://github.com/user-attachments/assets/3cee9952-7197-4fc7-8391-03af5eb916f0](https://github.com/user-attachments/assets/3cee9952-7197-4fc7-8391-03af5eb916f0)"\>
\<em\>A freshly generated plan with actionable tasks.\</em\>
\</p\>
\<p align="center"\>
\<img width="800" alt="Profile Page" src="[https://github.com/user-attachments/assets/241035fc-9286-4be8-b87e-9d6f8f7d2b4a](https://github.com/user-attachments/assets/241035fc-9286-4be8-b87e-9d6f8f7d2b4a)"\>
\<em\>The Profile Page, where all your plans and progress live.\</em\>
\</p\>
\<p align="center"\>
\<img width="800" alt="Home Page" src="[https://github.com/user-attachments/assets/b8838334-23cc-4a7f-bfd0-edc516fdc642](https://github.com/user-attachments/assets/b8838334-23cc-4a7f-bfd0-edc516fdc642)"\>
\<em\>The Home Page, where you enter your goal.\</em\>
\</p\>
\</details\>

-----

## Key Features

  - **AI-Powered Planning:** Utilizes a multi-model AI chain to break down goals into detailed, structured tasks.
  - **Dynamic Task Elaboration:** A secondary AI model enriches each task with descriptions, durations, dependencies, phases, and priorities.
  - **Robust and Resilient:** Implements robust JSON parsing with fallback mechanisms to ensure plan generation even when primary AI providers fail.
  - **User Authentication:** Simple and secure JWT cookie-based authentication for user login and signup.
  - **Persistent Storage:** All plans, tasks, and progress are saved to a database using SQLModel.
  - **Progress Tracking:** Easily track task completion and view overall project progress percentages.
  - **Seamless User Experience:** Built with **htmx** and **TailwindCSS** for a smooth, single-page application feel without the complexity of a heavy frontend framework.

-----

## Technology and Architecture

This project is built with a modern Python backend and a progressively enhanced frontend, designed for simplicity and power.

### Core Technologies

| Category         | Technology                               |
| :--------------- | :--------------------------------------- |
| **Backend** | FastAPI, SQLModel (ORM)                  |
| **Frontend** | Jinja2, TailwindCSS, htmx                |
| **AI Integration**| LiteLLM (for OpenAI, Anthropic, Gemini)  |
| **Authentication**| python-jose (JWT), passlib[bcrypt]       |
| **Database** | SQLite (default), PostgreSQL compatible  |
| **Async Tasks** | Celery with Redis (Optional)             |

### Architectural Flow

The application follows a simple yet effective request-response cycle, enhanced by htmx for partial page updates.

```
User Interface (htmx) ➡️ FastAPI API (/api/generate-plan) ➡️ LLM Service (Multi-model AI) ➡️ Database (SQLModel) ➡️ Render HTML Fragment ➡️ Redirect to Profile
```

-----

## How It Works: The AI Planning Engine

To ensure high-quality and diverse plans, the Smart Task Planner uses a two-stage AI reasoning process:

1.  **Stage 1: Task Drafting**
    The first AI model receives the user's goal and generates a concise list of 5–8 high-level task names. This stage focuses on brainstorming the core steps.

2.  **Stage 2: Task Elaboration**
    A second AI model takes each task name and expands it into a detailed object, defining its description, estimated duration, dependencies, project phase, and priority.

This multi-model approach prevents repetitive outputs and enriches the final plan. The system is provider-agnostic, thanks to **LiteLLM**, and includes graceful fallbacks to a rule-based planner if no AI API keys are available.

-----

## Getting Started

Follow these steps to set up and run the project locally.

### 1\. Prerequisites

  - Python 3.8+
  - An active Redis server (only if using Celery for background tasks).

### 2\. Installation

Clone the repository and install the required Python dependencies.

```bash
git clone https://github.com/your-username/smart-task-planner.git
cd smart-task-planner
pip install -r requirements.txt
```

Alternatively, install packages manually:

```bash
pip install fastapi uvicorn jinja2 python-multipart sqlmodel sqlalchemy python-dotenv
pip install passlib[bcrypt] python-jose[cryptography]
pip install litellm redis celery
```

### 3\. Environment Configuration

Create a `.env` file in the root directory and add your configuration variables.

```dotenv
# .env file

# --- Database ---
# Use a file-based SQLite database
DATABASE_URL=sqlite:///smart.db

# --- AI Providers ---
# Add at least one of the following API keys
OPENAI_API_KEY="your-openai-api-key"
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-google-gemini-api-key"
```

### 4\. Running the Application

Launch the FastAPI server. The database tables will be created automatically on the first run.

```bash
uvicorn app.main:app --reload
```

The application will be available at `http://127.0.0.1:8000`.

### 5\. (Optional) Running the Celery Worker

If you plan to use background tasks for plan generation, start the Celery worker in a separate terminal.

```bash
celery -A app.celery_config.celery_app worker -l info
```

-----

## API Endpoints

The backend exposes the following endpoints:

| Method | Endpoint                       | Description                                            |
| :----- | :----------------------------- | :----------------------------------------------------- |
| `GET`  | `/`                            | Renders the home page for goal input.                  |
| `GET`  | `/profile`                     | Displays the user's saved plans and progress.          |
| `GET`  | `/signup`                      | Renders the user registration page.                    |
| `POST` | `/signup`                      | Processes new user registration.                       |
| `GET`  | `/login`                       | Renders the user login page.                           |
| `POST` | `/login`                       | Processes user login and sets an auth cookie.          |
| `GET`  | `/logout`                      | Logs the user out and clears the auth cookie.          |
| `POST` | `/api/generate-plan`           | Main API to generate a plan from a user's goal.        |
| `POST` | `/api/submit-task/{task_id}`   | Toggles a task's status between submitted/not submitted. |
| `POST` | `/api/toggle-task/{task_id}`   | Toggles a task's status between submitted/completed.   |

-----

## Project Structure

```
├── app/
│   ├── main.py          # FastAPI routes and core application logic
│   ├── llm_service.py   # Multi-model AI planning and fallback logic
│   ├── models.py        # SQLModel database entities and enums
│   ├── database.py      # Database engine setup and table creation
│   ├── security.py      # Password hashing and JWT cookie authentication
│   ├── tasks.py         # Celery task definitions (optional)
│   └── celery_config.py # Celery application setup (optional)
├── templates/           # Jinja2 HTML templates
└── .env                 # Environment variables (not committed)
```

\<details\>
\<summary\>\<strong\>Additional Notes & Evaluation Details\</strong\>\</summary\>

#### Notes

  - The service intelligently cycles through available LLM provider keys, with fallbacks for failed API calls.
  - If no LLM keys are configured, a rule-based planner provides a sensible default plan to ensure functionality.
  - Task status casing is unified to uppercase (e.g., `SUBMITTED`, `COMPLETED`) for backend and frontend consistency.

#### Mapping to Professor’s Requirements

  - **Objective Met:** Goals are successfully broken down into actionable tasks with timelines and dependencies.
  - **Backend API:** The `/api/generate-plan` endpoint processes user input and generates a complete plan.
  - **Database Integration:** Plans and tasks are persisted via SQLModel.
  - **LLM Reasoning:** The multi-model workflow ensures richer, task-specific outputs.
  - **Prompt Engineering:** System and user prompts enforce structured JSON output, including phases, dependencies, and deadlines.
  - **Deliverables:** The codebase and this README serve as the primary deliverables. A short demo video can showcase the goal-to-plan-to-profile workflow.

\</details\>
