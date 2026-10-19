
---

## Running the project locally

**Prerequisites**
- Python 3.12 or newer
- Node.js 20.19 or newer
- Accounts for Groq, Qdrant Cloud and MongoDB Atlas, with their keys and connection strings

The project uses two terminals: one for the backend, one for the frontend.

### Terminal 1: backend

```bash
cd backend

# 1. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 2. Install the dependencies
pip install -r requirements.txt

# 3. Start the API server
uvicorn app.main:app --reload
```

The server runs at `http://127.0.0.1:8000`. API documentation is available at `http://127.0.0.1:8000/docs`.

The first time, you also need to load the data once (in another terminal, with the virtual environment activated):

```bash
cd backend
python -m app.rag.ingest_medlineplus    # loads the medical documents into Qdrant
python -m app.db.seed_doctors           # loads the sample doctors into MongoDB
```

### Terminal 2: frontend

```bash
cd frontend

# 1. Install the dependencies (first time only)
npm install

# 2. Start the development server
npm run dev
```

Open `http://localhost:5173` in your browser. The development server forwards all API calls to the backend, so no extra configuration is needed.

### Stopping the servers

Press `Ctrl+C` in each terminal.

---

## Testing

Start the backend first, then run these in a third terminal:

```bash
cd backend
source venv/bin/activate

python check_batch2.py    # chat, documents, emergencies, symptom intake
python check_batch3.py    # sign-up, login, slots, booking rules, cancellation
```

Each check prints `PASS` or `FAIL`. The booking script creates test accounts (`check-...@example.test`) and cancels its test appointments when it finishes.

---

## API reference

| Method | Path | Login | Description |
|---|---|---|---|
| GET | `/health` | no | Server status |
| POST | `/chat` | no | Send a message; returns an answer, an intake question or doctor cards |
| DELETE | `/chat/{session_id}` | no | Clear a chat and its symptom intake |
| POST | `/auth/signup` | no | Create an account; returns a token |
| POST | `/auth/login` | no | Log in; returns a token |
| GET | `/auth/me` | yes | The logged-in user |
| GET | `/doctors/{doctor_id}/slots` | no | Free 30-minute slots for the next 7 days |
| POST | `/appointments` | yes | Book a slot (optionally share the symptom summary) |
| GET | `/appointments/me` | yes | My upcoming and past appointments |
| POST | `/appointments/{id}/cancel` | yes | Cancel my appointment |

---

## Safety design

- **Layered checks.** Emergency phrases are checked before any model call. The router's urgency is checked next. The intake also runs a red-flag check after every answer.
- **No diagnosis and no dosage.** The prompts forbid naming a condition for the user and giving medicine doses. Sensitive questions receive an extra rule.
- **Grounded answers.** Answers are built only from retrieved passages. Low-scoring matches are not used.
- **Privacy.** Passwords are never stored in plain text or returned by the API. Each patient can see only their own appointments. A symptom summary is shared with a doctor only if the patient ticks the box, and only after a finished intake.
- **Honest fallback.** When nothing relevant is found, the answer says so and is labelled as general information.

---

## Data sources and attribution

- **Health topics:** [MedlinePlus.gov](https://medlineplus.gov/), National Library of Medicine. Answers that use this content are marked "Information from MedlinePlus.gov".
- **Doctors, specialties, fees and schedules:** fictional sample data created for this project.
- **Red-flag phrases and intake rules:** simple demonstration rules written for learning. They are not clinical guidelines and must be reviewed by a clinician before any real use.

---

## Limitations

- The embedding model works best in English, so Roman Urdu questions can be less accurate.
- Only one document source (MedlinePlus) is loaded.
- Free-tier hosting may sleep and respond slowly on the first request.
- Doctor availability comes from a weekly schedule. Rescheduling and payments are not supported.
- There are no email or SMS reminders yet.
- Login tokens are stored in the browser's `localStorage`. This is acceptable for a learning project, but a production system should use a more secure approach such as HTTP-only cookies.
- This is not a medical device and must not be used with real patients.

---

## Roadmap

- Doctor accounts and a doctor dashboard that shows the patient's symptom summary
- An admin page with charts: frequent questions, knowledge gaps and urgency counts
- Email reminders for appointments
- An evaluation set (questions with expected sources) to measure retrieval and answer quality
- Support for Urdu-script questions and a multilingual embedding model

---

## Author

**Laiba**. Built as a portfolio project to explore retrieval-augmented generation, safety design and full-stack development.