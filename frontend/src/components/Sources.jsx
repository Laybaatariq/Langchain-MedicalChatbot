import { DocIcon } from "./Icons.jsx";

export default function Sources({ sources }) {
  if (!sources?.length) return null;

  return (
    <details className="sources">
      <summary>
        <DocIcon />
        {sources.length === 1 ? "1 source" : `${sources.length} sources`}
      </summary>
      <ul>
        {sources.map((s, i) => (
          <li key={`${s.title}-${i}`}>
            <div className="source-head">
              <p className="source-title">{s.title}</p>
              {typeof s.score === "number" && (
                <span className="source-score">{Math.round(s.score * 100)}% match</span>
              )}
            </div>
            {s.snippet && <p className="source-snippet">{s.snippet}</p>}
          </li>
        ))}
      </ul>
    </details>
  );
}
