# Medical Chatbot

A portfolio project: a medical information chatbot that answers questions from trusted
medical documents, asks the right questions before suggesting a doctor, and lets a
patient book a fictional appointment.

> **Important.** This is a learning project and not a medical service. It does not
> diagnose, does not prescribe medicine or doses, and every doctor, fee and appointment
> is fictional sample data. In an emergency, call your local emergency number right away.

---

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [Run it locally](#run-it-locally)
- [Environment variables](#environment-variables)
- [Testing](#testing)
- [API reference](#api-reference)
- [Data sources and attribution](#data-sources-and-attribution)
- [Safety design](#safety-design)
- [Limitations](#limitations)
- [Possible next steps](#possible-next-steps)

---

## Features

**Grounded answers from documents**
- Questions are answered only from loaded medical documents (MedlinePlus Health Topics).
- Each answer lists its sources, with links to the MedlinePlus pages.
- Sources appear only when the answer really uses them.
- If no relevant passage is found, the answer is marked as general information.

**Understands English and Roman Urdu**
- Questions and answers can be in English or Roman Urdu (Urdu written in English letters).
- A router turns the question into a standalone English search query, so follow-up questions
  such as "how can I prevent it?" still find the right topic.

**Safety first**
- Emergency phrases (English and Roman Urdu) get a fixed emergency message, and no model
  answer is generated.
- A general question such as "what causes a stroke?" is answered normally, while "my father
  has a stroke" triggers the emergency message.
- Questions about diagnosis or medicine doses get general information only.

**Symptom intake**
- When someone describes a symptom, the bot asks one question at a time, with tap buttons.
- Questions include duration, severity (1 to 10), trend, other symptoms, and age.
- The patient can skip most questions, cancel at any time, or change the topic.
- A red-flag check runs after every answer.
- The result shows an urgency level (urgent, routine, or self-care), the reasons, and a
  suggested type of doctor. Children are sent to a pediatrician.

**Doctors and booking**
- Sample doctors are shown as cards with city, experience, fee and days.
- A patient signs up, picks a free 30-minute slot in the next 7 days, and confirms.
- The patient can choose to share the symptom summary with the doctor.
- Patients can see and cancel their own appointments.
- Rules: at least 2 hours ahead, at most 5 upcoming appointments, and no double booking.

**Accounts**
- Sign up and log in with email and password. Passwords are hashed with scrypt.
- Login uses a signed token (JWT) that lasts 24 hours.
- Chatting does not require login. Only booking does.

---

## Screenshots

### Chat and answers from documents

| | |
|---|---|
| **Greeting**<br>![Greeting](docs/screenshots/01-greeting.png) | **Answer from documents with sources**<br>![Documents answer](docs/screenshots/02-documents-answer.png) |
| **Follow-up question**<br>![Follow-up](docs/screenshots/03-followup.png) | **Roman Urdu answer**<br>![Roman Urdu](docs/screenshots/04-roman-urdu.png) |
| **Off-topic question**<br>![Off-topic](docs/screenshots/05-off-topic.png) | **General answer notice**<br>![General notice](docs/screenshots/06-general-notice.png) |

### Safety

| | |
|---|---|
| **General question, no alarm**<br>![Stroke question](docs/screenshots/07-general-not-emergency.png) | **Emergency message**<br>![Emergency](docs/screenshots/08-emergency.png) |
| **Emergency during the intake**<br>![Intake emergency](docs/screenshots/11-intake-emergency.png) | |

### Symptom intake and doctor suggestion

| | |
|---|---|
| **First intake question**<br>![Intake question](docs/screenshots/09-intake-question.png) | **Result with urgency and doctors**<br>![Intake result](docs/screenshots/10-intake-result.png) |
| **Stopping the intake**<br>![Cancel](docs/screenshots/12-intake-cancel.png) | |

### Accounts and booking

| | |
|---|---|
| **Booking a slot**<br>![Booking](docs/screenshots/13-booking.png) | **My appointments**<br>![Appointments](docs/screenshots/14-appointments.png) |
| **Account menu**<br>![Account menu](docs/screenshots/15-account-menu.png) | |

---

## How it works

```
Browser ──POST /chat──▶ Router (one LLM call)
                          │  intent, language, standalone English query, urgency
                          ▼
                 Safety check ──emergency──▶ fixed emergency message
                          │
          ┌───────────────┼──────────────────────┐
          ▼               ▼                      ▼
   Symptom intake   Small talk /            Medical question
   (MongoDB state,  off-topic reply         │
    one question)                           ▼
          │                         Qdrant search (top 6)
          ▼                                  │
   Urgency rules + doctor type               ▼
   + doctor cards                   Relevant passages?
                                     ├─ yes ──▶ answer from documents + sources
                                     └─ no  ──▶ labelled general answer
```

Step by step:

1. The browser sends the message to `POST /chat` with a session id.
2. The **router** makes one LLM call and returns the intent (`medical`, `symptom`, `chitchat`,
   `off_topic`), the language, a standalone English query, and an urgency level.
3. The **safety check** looks at emergency phrases (from `red_flags.json`), the regex
   filters and the router's urgency. An emergency stops the flow here.
4. For a **symptom**, the intake starts or continues. Its state (answers so far, step,
   status) is saved in MongoDB per chat session.
5. For a **medical question**, the app searches Qdrant. Only passages whose score is at
   least 0.5 (and close to the best match) are used. They go to the LLM with the question
   and the recent history.
6. **Booking** uses the logged-in user from the JWT token. The free slots are calculated
   from the doctor's weekly schedule in the clinic time zone.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI, Pydantic, Uvicorn |
| LLM | Groq (`openai/gpt-oss-120b`) through LangChain |
| Retrieval | Qdrant Cloud (vector search), fastembed (`BAAI/bge-small-en-v1.5`, runs locally) |
| Database | MongoDB Atlas (chat history, intake state, users, doctors, appointments) |
| Auth | JWT (PyJWT), scrypt password hashing (Python standard library) |
| Frontend | React, Vite, react-markdown |
| Data | MedlinePlus Health Topics XML (National Library of Medicine) |

---

## Project structure

```
backend/
├── app/
│   ├── main.py              app setup: routers, CORS, startup checks
│   ├── api/                 routes (chat, health, accounts, booking) and request/response models
│   ├── auth/                password hashing, JWT tokens, current-user dependency
│   ├── booking/             slot maths, booking rules, appointment database access
│   ├── chains/              router, answer chain and prompts
│   ├── intake/              symptom intake: flow, rules, texts, doctor lookup, state store
│   ├── rag/                 Qdrant vector store, MedlinePlus ingestion, debug search
│   ├── safety/              emergency phrases and helpers
│   ├── core/                settings, rule-file loader and consistency checks
│   ├── db/                  MongoDB connections (chat history, shared connection)
│   └── data/
│       ├── rules/           red_flags.json, specialties.json, intake_questions.json
│       ├── doctors/         doctors.json (fictional)
│       └── medlineplus/     mplus_topics.xml (downloaded, not in git)
├── check_batch2.py          end-to-end test: chat and intake
├── check_batch3.py          end-to-end test: accounts and booking
├── requirements.txt
└── .env                     secrets (not in git)

frontend/
├── src/
│   ├── App.jsx              layout, header, tabs, views
│   ├── api.js               backend calls (chat, accounts, booking)
│   ├── auth/                login state for the whole app
│   ├── components/          messages, sources, intake buttons, doctor cards,
│   │                        booking dialog, login form, account menu
│   ├── hooks/useChat.js     chat state and session
│   └── pages/Appointments.jsx
├── vite.config.js           dev proxy to the backend
└── package.json
```

---

## Run it locally

You need Python 3.12 (or newer), Node.js 20.19 or newer, and accounts for Groq,
Qdrant Cloud and MongoDB Atlas.

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` (see [Environment variables](#environment-variables)).

Put the MedlinePlus Health Topic XML file at
`backend/app/data/medlineplus/mplus_topics.xml`, then load it into Qdrant:

```bash
python -m app.rag.ingest_medlineplus
```

Load the sample doctors into MongoDB:

```bash
python -m app.db.seed_doctors
```

Start the server:

```bash
uvicorn app.main:app --reload
```

The API documentation is at `http://127.0.0.1:8000/docs`.

### 2. Frontend

In a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. The Vite dev server forwards API calls to the backend,
so no CORS setup is needed for local development.

### Check your setup

```bash
cd backend
python -m app.core.knowledge                              # rule files and sample doctors are consistent
python -m app.rag.debug_search "what causes migraines"    # retrieval scores
```

---

## Testing

With the backend running:

```bash
cd backend
python check_batch2.py    # chat, documents, emergencies, symptom intake
python check_batch3.py    # signup, login, slots, booking rules, cancel
```

Each check prints `PASS` or `FAIL`. The booking script creates test accounts
(`check-...@example.test`) and cancels its test appointments at the end.

---

## API reference

| Method | Path | Login | Description |
|---|---|---|---|
| GET | `/health` | no | server status |
| POST | `/chat` | no | send a message; returns an answer, an intake question, or doctor cards |
| DELETE | `/chat/{session_id}` | no | clear a chat and its symptom intake |
| POST | `/auth/signup` | no | create an account; returns a token |
| POST | `/auth/login` | no | log in; returns a token |
| GET | `/auth/me` | yes | the logged-in user |
| GET | `/doctors/{doctor_id}/slots` | no | free 30-minute slots for the next 7 days |
| POST | `/appointments` | yes | book a slot (optionally share the symptom summary) |
| GET | `/appointments/me` | yes | my upcoming and past appointments |
| POST | `/appointments/{id}/cancel` | yes | cancel my appointment |

---

## Data sources and attribution

- **Health topics:** [MedlinePlus.gov](https://medlineplus.gov/), National Library of Medicine.
  The app shows "Information from MedlinePlus.gov" under answers that use it.
- **Doctors, specialties, fees and schedules:** fictional sample data written for this project.
- **Red-flag phrases and intake rules:** simple demonstration rules written for learning.
  They are not clinical guidelines and must be reviewed by a clinician before any real use.

---

## Safety design

- **Layers.** Emergency phrases are checked first (before any model call). Then the router's
  urgency is checked. Then the intake's red-flag check runs after every answer.
- **No diagnosis, no dosage.** The answer prompts forbid naming a condition for the user and
  giving medicine doses. Sensitive questions get an extra rule.
- **Grounding.** Answers come from retrieved passages. A low-score match is not used.
- **Privacy.** Passwords are never stored in plain text and never returned by the API.
  Each patient sees only their own appointments. The symptom summary is shared only when the
  patient ticks the box, and only after a finished intake.
- **Honest answers.** If nothing relevant is found, the answer says so and is labelled as
  general information.

---

## Limitations

- The embedding model works best in English, so Roman Urdu questions can be less accurate.
- Only one document source (MedlinePlus) is loaded.
- Free-tier hosting can sleep and is slow on the first request.
- Doctor availability comes from a weekly schedule. There is no rescheduling and no payment.
- No email or SMS reminders yet.
- The tokens are kept in the browser's `localStorage`. That is acceptable for a learning
  project, but a production app should use a safer method (for example, secure cookies).
- Not a medical device and not for real patients.

---

## Possible next steps

- Doctor login and a doctor dashboard (see the patient's symptom summary).
- An admin page with charts: common questions, knowledge gaps, urgency counts.
- Email reminders for appointments.
- An evaluation set (questions with expected sources) to measure retrieval and answer quality.
- Urdu-script questions and a multilingual embedding model.

---

## Author

Laiba. Built as a portfolio project to learn retrieval-augmented generation, safety design
and full-stack development.