import { useEffect, useRef, useState } from "react";
import { useAuth } from "./auth/AuthContext.jsx";
import AccountMenu from "./components/AccountMenu.jsx";
import AuthForm from "./components/AuthForm.jsx";
import BookingDialog from "./components/BookingDialog.jsx";
import Composer from "./components/Composer.jsx";
import EmptyState from "./components/EmptyState.jsx";
import { CrossMark, InfoIcon } from "./components/Icons.jsx";
import Message from "./components/Message.jsx";
import Modal from "./components/Modal.jsx";
import { useChat } from "./hooks/useChat.js";
import Appointments from "./pages/Appointments.jsx";

export default function App() {
  const { messages, sessionId, loading, error, send, retry, reset } = useChat();
  const { user, signOut } = useAuth();
  const [view, setView] = useState("chat"); // "chat" | "appointments"
  const [bookingDoctor, setBookingDoctor] = useState(null);
  const [showLogin, setShowLogin] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    if (view === "chat") endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, error, view]);

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

          <nav className="nav" aria-label="Main">
            <button
              type="button"
              className={`nav-link${view === "chat" ? " active" : ""}`}
              aria-current={view === "chat" ? "page" : undefined}
              onClick={() => setView("chat")}
            >
              Chat
            </button>
            <button
              type="button"
              className={`nav-link${view === "appointments" ? " active" : ""}`}
              aria-current={view === "appointments" ? "page" : undefined}
              onClick={() => setView("appointments")}
            >
              My appointments
            </button>
          </nav>

          <div className="account">
            <AccountMenu
              user={user}
              onLogin={() => setShowLogin(true)}
              onOpenAppointments={() => setView("appointments")}
              onLogout={signOut}
            />
          </div>
        </div>
      </header>

      <main className="thread">
        <div className="container" aria-live="polite">
          {view === "appointments" ? (
            <Appointments onLogin={() => setShowLogin(true)} />
          ) : (
            <>
              {messages.length === 0 ? (
                <EmptyState onPick={send} />
              ) : (
                messages.map((m, i) => (
                  <Message
                    key={i}
                    message={m}
                    isLast={i === messages.length - 1}
                    onReply={send}
                    onBook={setBookingDoctor}
                    busy={loading}
                  />
                ))
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
            </>
          )}
        </div>
      </main>

      {view === "chat" && (
        <footer className="footer">
          <div className="container">
            <Composer
              onSend={send}
              onNewChat={reset}
              canStartNew={messages.length > 0}
              disabled={loading}
            />
            <p className="footnote">
              <InfoIcon />
              General information only. For urgent symptoms, contact your local emergency number.
            </p>
          </div>
        </footer>
      )}

      {bookingDoctor && (
        <BookingDialog doctor={bookingDoctor} sessionId={sessionId} onClose={() => setBookingDoctor(null)} />
      )}

      {showLogin && (
        <Modal title="Log in" onClose={() => setShowLogin(false)}>
          <AuthForm onDone={() => setShowLogin(false)} />
        </Modal>
      )}
    </div>
  );
}