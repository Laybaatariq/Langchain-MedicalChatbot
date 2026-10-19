import { useRef, useState } from "react";
import { PlusIcon, SendIcon } from "./Icons.jsx";

const MAX_LENGTH = 2000; // matches the backend limit on ChatRequest.message

/**
 * The message box.
 *   onSend:      sends the typed text
 *   onNewChat:   the "+" button on the left starts a fresh conversation
 *   canStartNew: false while the chat is still empty (nothing to clear)
 *   disabled:    true while waiting for the server
 */
export default function Composer({ onSend, onNewChat, canStartNew = true, disabled }) {
  const [text, setText] = useState("");
  const ref = useRef(null);

  function submit() {
    if (!text.trim() || disabled) return;
    onSend(text);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  }

  function handleKeyDown(e) {
    // Enter sends, Shift+Enter adds a new line
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  }

  function handleInput(e) {
    setText(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  return (
    <div className="composer">
      <button
        type="button"
        className="new-chat"
        aria-label="New chat"
        title="New chat"
        onClick={onNewChat}
        disabled={!canStartNew || disabled}
      >
        <PlusIcon />
      </button>
      <label htmlFor="message" className="visually-hidden">
        Your question
      </label>
      <textarea
        id="message"
        ref={ref}
        rows={1}
        value={text}
        maxLength={MAX_LENGTH}
        placeholder="Describe your question, e.g. what causes migraines?"
        onChange={handleInput}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        className="send"
        onClick={submit}
        disabled={disabled || !text.trim()}
        aria-label="Send message"
      >
        <SendIcon />
      </button>
    </div>
  );
}