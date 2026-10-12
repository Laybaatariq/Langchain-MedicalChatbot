import ReactMarkdown from "react-markdown";
import DoctorCards from "./DoctorCards.jsx";
import { AlertIcon, CrossMark, InfoIcon } from "./Icons.jsx";
import QuickReplies from "./QuickReplies.jsx";
import Sources from "./Sources.jsx";

function Emergency({ text }) {
  return (
    <div className="emergency" role="alert">
      <span className="emergency-icon">
        <AlertIcon />
      </span>
      <div>
        <p className="emergency-title">This may be an emergency</p>
        <p className="emergency-text">{text}</p>
      </div>
    </div>
  );
}

/**
 * isLast:  only the newest answer shows its quick-reply buttons
 * onReply: sends a button's text as the patient's message
 * busy:    true while waiting for the server
 */
export default function Message({ message, isLast = false, onReply, busy = false }) {
  if (message.role === "user") {
    return (
      <div className="row row-user">
        <p className="bubble-user">{message.content}</p>
      </div>
    );
  }

  if (message.category === "EMERGENCY") {
    return (
      <div className="row">
        <Emergency text={message.content} />
      </div>
    );
  }

  return (
    <div className="row row-assistant">
      <span className="avatar" aria-hidden="true">
        <CrossMark size={16} />
      </span>
      <div className="answer">
        {message.progress && <p className="progress">{message.progress.label}</p>}

        {message.urgency && message.urgencyLabel && (
          <p className={`urgency urgency-${message.urgency}`}>{message.urgencyLabel}</p>
        )}

        {/* Answer did not come from the loaded documents */}
        {message.notice && <p className="notice">{message.notice}</p>}

        {message.category === "SENSITIVE" && (
          <p className="note">
            This touches on diagnosis or medication, so the answer stays general.
          </p>
        )}

        <div className="prose">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        <DoctorCards doctors={message.doctors} />

        <Sources sources={message.sources} />

        {message.disclaimer && (
          <p className="disclaimer">
            <InfoIcon />
            <span>{message.disclaimer}</span>
          </p>
        )}

        {isLast && message.quickReplies && (
          <QuickReplies data={message.quickReplies} onPick={onReply} disabled={busy} />
        )}
      </div>
    </div>
  );
}