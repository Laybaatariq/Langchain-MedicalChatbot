import { useEffect, useRef } from "react";
import Composer from "./components/Composer.jsx";
import EmptyState from "./components/EmptyState.jsx";
import { CrossMark, InfoIcon } from "./components/Icons.jsx";
import Message from "./components/Message.jsx";
import { useChat } from "./hooks/useChat.js";

export default function App() {
  const { messages, loading, error, send, retry, reset } = useChat();
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, error]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="container topbar-inner">
          <div className="brand">
            <span className="logo" aria-hidden="true">
              <CrossMark size={20} />
            </span>
            <div>
              <h1>Medical Chatbot</h1>
              <p>Health information grounded in medical documents</p>
            </div>
          </div>
          <button type="button" className="ghost" onClick={reset} disabled={!messages.length}>
            New chat
          </button>
        </div>
      </header>

      <main className="thread">
        <div className="container" aria-live="polite">
          {messages.length === 0 ? (
            <EmptyState onPick={send} />
          ) : (
            messages.map((m, i) => <Message key={i} message={m} />)
          )}

          {loading && (
            <div className="row row-assistant" aria-label="Looking up an answer">
              <span className="avatar" aria-hidden="true">
                <CrossMark size={16} />
              </span>
              <div className="typing">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          {error && (
            <div className="error" role="alert">
              <p>{error}</p>
              <button type="button" onClick={retry} disabled={loading}>
                Try again
              </button>
            </div>
          )}

          <div ref={endRef} />
        </div>
      </main>

      <footer className="footer">
        <div className="container">
          <Composer onSend={send} disabled={loading} />
          <p className="footnote">
            <InfoIcon />
            General information only. For urgent symptoms, contact your local emergency number.
          </p>
        </div>
      </footer>
    </div>
  );
}
