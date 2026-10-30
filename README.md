# CreatorOS

CreatorOS is an AI-powered LinkedIn content studio. It learns a creator's writing style, plans and generates posts, reviews drafts through multiple agents, evaluates content quality, and helps the creator learn from post-performance feedback. It also supports scheduling approved posts and showing in-app reminders when they are due. CreatorOS does **not** automatically publish to LinkedIn.

## Features

- **Brand voice profiling:** learns a reusable writing profile from 3–10 sample posts.
- **AI content generation:** creates a LinkedIn post from a user-provided topic.
- **Multi-agent review:** Strategist, Writer, Editor, and Evaluator cooperate to produce and refine a draft.
- **Self-evaluation:** scores the initial and final drafts against a seven-criterion rubric.
- **Human approval:** the creator reviews and approves a generated post before it can be scheduled.
- **AI-generated visuals:** can generate an image for a post through the configured Mesh image-generation model.
- **Content history:** stores and displays previously generated posts.
- **Performance tracking:** records manual LinkedIn metrics and audience comments; simulated metrics are clearly labelled as simulated.
- **Learning loop:** analyses performance feedback and proposes lessons for human approval. Approved lessons can inform future content generation.
- **Post scheduling:** schedules approved posts and marks them due. The application shows an in-app reminder; the creator publishes manually on LinkedIn and can then mark the schedule as published.

## Architecture

### How the agents cooperate

The content-generation workflow is orchestrated with LangGraph:

1. **Strategist** interprets the topic and brand voice, then selects a content angle and explains the strategy.
2. **Writer** creates the initial LinkedIn draft using the selected angle, brand voice, and relevant approved learning lessons.
3. **Evaluator (initial evaluation)** independently scores the first draft and identifies areas that could be improved.
4. **Editor** reviews the draft against the content requirements and either approves it or provides revision feedback.
5. **Writer and Editor** repeat the revision/review cycle within the configured revision limit.
6. **Evaluator (final evaluation)** scores the final draft independently and compares it with the initial evaluation.
7. **Human review** remains part of the workflow: the creator decides whether to approve the generated post.

The Evaluator does not simply copy the Editor's verdict. It assesses the draft against the rubric independently.

### Self-evaluation rubric

Each criterion contributes to a total score of 100:

| Criterion | Maximum score |
|---|---:|
| Technical accuracy | 25 |
| Practical value | 20 |
| Brand voice alignment | 15 |
| Readability | 15 |
| Conciseness | 10 |
| Topic relevance | 10 |
| Engagement potential | 5 |
| **Total** | **100** |

CreatorOS stores the initial and final evaluation for each generated post and calculates the score change. The actual scores depend on the generated content; there is no single fixed project-wide score.

### Technology

- **Backend:** Python, FastAPI, SQLAlchemy
- **Frontend:** React
- **Agent orchestration:** LangGraph
- **LLM client:** OpenAI Python SDK configured with the Mesh API base URL
- **AI provider gateway:** Mesh API (`https://api.meshapi.ai/v1`)
- **Database:** PostgreSQL
- **Scheduling:** APScheduler
- **Image generation:** Mesh image-generation model configured through the backend

All LLM calls must go through Mesh API. Do not replace the Mesh base URL with the standard OpenAI endpoint.

## Repository layout

The repository should contain the source files and folders used by the application. The main areas are:

```text
.
├── agents/                 # Strategist, Writer, Editor, Evaluator
├── graph/                  # LangGraph state and workflow
├── models/                 # SQLAlchemy models
├── services/               # Mesh AI, image generation, learning services
├── frontend/               # React application
│   └── src/
├── tests/                  # Automated tests
├── api.py                  # FastAPI application and API routes
├── config.py               # Environment/configuration loading
├── database.py             # SQLAlchemy engine, Base, sessions
├── init_db.py              # Creates tables in an existing database
├── requirements.txt
├── .env.example            # Example variable names; no real secrets
├── .gitignore
└── README.md
```

Your actual repository may contain additional modules. Keep all source files required by your imports and workflows.

## Prerequisites

Install the following before running CreatorOS:

- Python 3.12 (recommended, matching the development environment)
- Node.js and npm
- PostgreSQL
- Git
- A Mesh API key
- LinkedIn application credentials for the LinkedIn OAuth sign-in flow

### PostgreSQL database setup

**Important:** Create the PostgreSQL database before running `init_db.py`. The project initialization script creates the application's tables; it does not create the PostgreSQL database itself.

For example, using `psql`:

```sql
CREATE DATABASE creatoros;
CREATE USER creatoros_app WITH PASSWORD 'replace-with-a-strong-password';
GRANT ALL PRIVILEGES ON DATABASE creatoros TO creatoros_app;
```

Connect to the new database and grant schema permissions (for PostgreSQL versions/configurations that require explicit schema privileges):

```sql
\c creatoros
GRANT USAGE, CREATE ON SCHEMA public TO creatoros_app;
```

The example uses PostgreSQL's default `public` schema. If you use a different schema, configure the database connection and permissions accordingly.

The database role and password above are examples. Use your own secure credentials.

## Configuration

Create a local `.env` file in the backend project root. Do not commit this file.

Add the variables required by your current `config.py`, database configuration, and LinkedIn OAuth implementation. For example:

```dotenv
MESH_API_KEY=your_mesh_api_key
MESH_MODEL=amazon/nova-micro-v1

# Use the exact PostgreSQL connection variable expected by database.py.
# Example SQLAlchemy URL for psycopg 3:
DATABASE_URL=postgresql+psycopg://creatoros_app:replace-with-a-strong-password@localhost:5432/creatoros

# Add the LinkedIn OAuth and session variables required by your api.py.
# Use the exact variable names read by your current backend code.
```

The Mesh base URL is configured in `config.py` as:

```text
https://api.meshapi.ai/v1
```

Do not put `MESH_API_KEY`, LinkedIn client secrets, session secrets, or database passwords in frontend code, source control, or public screenshots.

> **Before sharing this README:** Check `database.py`, `api.py`, and your local `.env` and replace the example database variable/placeholder comments with the exact environment variable names used by your current code. Never paste actual secret values into this file.

## Installation and running locally

Run the following commands from the repository root.

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_DIRECTORY>
```

### 2. Create and activate a Python virtual environment

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install backend dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Make sure `requirements.txt` includes APScheduler, as the scheduler feature uses it. If it is not already listed, add the version used by the project, for example:

```text
APScheduler==3.11.0
```

### 4. Configure environment variables

Create `.env` using the Configuration section above. Add valid Mesh API credentials and the required PostgreSQL and LinkedIn OAuth settings.

### 5. Create the database tables

After PostgreSQL is running and the `creatoros` database exists:

```bash
python init_db.py
```

This runs SQLAlchemy `Base.metadata.create_all()` and creates missing tables registered by the imported models. It does not create the database, and it does not alter existing table definitions.

### 6. Start the backend

Open a terminal at the repository root, activate `.venv`, then run:

```bash
uvicorn api:app --reload
```

The API should be available at:

```text
http://127.0.0.1:8000
```

FastAPI's interactive API documentation is normally available at:

```text
http://127.0.0.1:8000/docs
```

If your application uses a different ASGI variable name or module path, use the corresponding import path from `api.py`.

### 7. Start the frontend

Open a **second terminal**:

```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite in the terminal (commonly `http://localhost:5173`).

If the frontend uses a different development script, check `frontend/package.json` and run the script listed there.

### 8. Use CreatorOS

1. Sign in through LinkedIn OAuth.
2. Add at least three sample posts to create a brand voice.
3. Generate a post by entering a topic.
4. Review the post and its evaluation.
5. Approve the post if you want to schedule it.
6. Open Scheduler, choose a future date and time, and schedule it.
7. Keep the backend running. When the scheduled time arrives, CreatorOS marks the schedule due and displays an in-app reminder.
8. Publish the post manually on LinkedIn, then use **Mark as published** in CreatorOS to close the reminder.
9. Add performance metrics and audience comments to generate learning suggestions. Approve useful lessons so future content can use them.

## Scheduler notes

- PostgreSQL is the persistent source of truth for scheduled posts.
- APScheduler runs in the backend process and marks elapsed schedules as due.
- The frontend periodically refreshes schedule data and shows due reminders while the app is open.
- This initial implementation is intended to run with **one backend process/worker**. Do not start multiple Uvicorn workers or multiple backend instances with the in-process scheduler. A multi-instance deployment needs a distributed scheduler or database-backed locking strategy.
- CreatorOS does not automatically publish posts to LinkedIn. Due posts must be published manually.
- The in-app reminder is not an email, browser push, or macOS desktop notification.

## Running tests

Activate the virtual environment, then run:

```bash
pytest
```

For coverage, if configured in the project:

```bash
pytest --cov
```

### Before pushing

```bash
# Check for accidentally staged secrets
git status

# Confirm .env is ignored
git check-ignore .env

# Compile Python files
python -m compileall -q .

# Run tests
pytest
```

Do not use `git add .env`. If `.env` was committed previously, adding it to `.gitignore` does not remove it from Git history; remove it from tracking and rotate any exposed credentials.

## Security

- Keep `.env` local and out of Git.
- Use GitHub Actions repository secrets for CI credentials.
- Never expose Mesh or LinkedIn credentials in React code.
- Use a separate database role with only the permissions the application needs.
- Do not commit real user data, OAuth tokens, generated private content, or database dumps.
