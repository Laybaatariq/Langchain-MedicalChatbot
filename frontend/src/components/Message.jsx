import ReactMarkdown from "react-markdown";
import { AlertIcon, CrossMark, InfoIcon } from "./Icons.jsx";
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

export default function Message({ message }) {
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
        {message.category === "SENSITIVE" && (
          <p className="note">
            This touches on diagnosis or medication, so the answer stays general.
          </p>
        )}
        <div className="prose">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>
        <Sources sources={message.sources} />
        {message.disclaimer && (
          <p className="disclaimer">
            <InfoIcon />
            <span>{message.disclaimer}</span>
          </p>
        )}
      </div>
    </div>
  );
}
