import { useState } from "react";

/**
 * Buttons under a question asked by the symptom intake.
 *   mode "single": tapping an option sends it right away
 *   mode "multi":  tap several options, then the confirm button sends them together
 *   mode "text":   only the Skip button (the patient types the answer)
 * Sending an option is the same as typing it, so the backend needs no special API.
 */
export default function QuickReplies({ data, onPick, disabled }) {
  const [selected, setSelected] = useState([]);

  if (!data) return null;
  const { mode, options = [], skip_label: skipLabel, confirm_label: confirmLabel } = data;

  const toggle = (option) =>
    setSelected((current) =>
      current.includes(option) ? current.filter((o) => o !== option) : [...current, option]
    );

  // keep the order of the options, not the order of the taps
  const sendSelected = () => onPick(options.filter((o) => selected.includes(o)).join(", "));

  return (
    <div className="quick" role="group" aria-label="Quick replies">
      {options.map((option) =>
        mode === "multi" ? (
          <button
            key={option}
            type="button"
            className="chip"
            aria-pressed={selected.includes(option)}
            disabled={disabled}
            onClick={() => toggle(option)}
          >
            {option}
          </button>
        ) : (
          <button key={option} type="button" className="chip" disabled={disabled} onClick={() => onPick(option)}>
            {option}
          </button>
        )
      )}

      {mode === "multi" && (
        <button
          type="button"
          className="chip chip-confirm"
          disabled={disabled || selected.length === 0}
          onClick={sendSelected}
        >
          {confirmLabel || "Done"}
        </button>
      )}

      {skipLabel && (
        <button type="button" className="chip chip-skip" disabled={disabled} onClick={() => onPick(skipLabel)}>
          {skipLabel}
        </button>
      )}
    </div>
  );
}