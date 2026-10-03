import { CheckIcon, CrossMark } from "./Icons.jsx";

const STARTERS = [
  { topic: "Symptoms", question: "What are the common symptoms of diabetes?" },
  { topic: "Prevention", question: "How can high blood pressure be prevented?" },
  { topic: "Causes", question: "What causes migraines?" },
];

const PROMISES = [
  "Every answer shows the sources it came from",
  "No diagnoses and no medication doses",
  "Urgent symptoms are flagged right away",
];

export default function EmptyState({ onPick }) {
  return (
    <section className="empty">
      <span className="empty-mark" aria-hidden="true">
        <CrossMark size={26} />
      </span>
      <h2>Ask about symptoms, conditions or treatments</h2>
      <p className="empty-lead">
        Get clear, general health information drawn from the medical documents loaded into this app.
      </p>

      <ul className="starters">
        {STARTERS.map((s) => (
          <li key={s.question}>
            <button type="button" onClick={() => onPick(s.question)}>
              <span className="starter-topic">{s.topic}</span>
              <span className="starter-question">{s.question}</span>
            </button>
          </li>
        ))}
      </ul>

      <ul className="promises">
        {PROMISES.map((p) => (
          <li key={p}>
            <CheckIcon />
            {p}
          </li>
        ))}
      </ul>
    </section>
  );
}
