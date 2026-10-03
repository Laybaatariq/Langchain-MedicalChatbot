import { useCallback, useEffect, useRef, useState } from "react";
import { deleteChat, sendChat } from "../api.js";

const STORAGE_KEY = "medchat:v1";

function load() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Array.isArray(saved.messages)) return saved;
  } catch {
    /* storage unavailable or corrupted - start fresh */
  }
  return { sessionId: null, messages: [] };
}

export function useChat() {
  const [{ sessionId, messages }, setChat] = useState(load);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const lastText = useRef("");

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId, messages }));
    } catch {
      /* ignore */
    }
  }, [sessionId, messages]);

  const send = useCallback(
    async (text, { isRetry = false } = {}) => {
      const message = text.trim();
      if (!message || loading) return;

      lastText.current = message;
      setError(null);
      setLoading(true);

      if (!isRetry) {
        setChat((c) => ({ ...c, messages: [...c.messages, { role: "user", content: message }] }));
      }

      try {
        const data = await sendChat({ message, sessionId });
        setChat((c) => ({
          sessionId: data.session_id,
          messages: [
            ...c.messages,
            {
              role: "assistant",
              content: data.reply,
              category: data.category,
              sources: data.sources || [],
              disclaimer: data.disclaimer,
            },
          ],
        }));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    },
    [loading, sessionId]
  );

  const retry = useCallback(() => send(lastText.current, { isRetry: true }), [send]);

  const reset = useCallback(() => {
    deleteChat(sessionId);
    setChat({ sessionId: null, messages: [] });
    setError(null);
  }, [sessionId]);

  return { messages, loading, error, send, retry, reset };
}
