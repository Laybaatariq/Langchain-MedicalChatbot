// Empty in development: requests go to the Vite dev server, which proxies them to the backend.
// For a deployed frontend, set VITE_API_URL to the backend URL (e.g. https://my-api.example.com).
const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

/** POST /chat -> { session_id, reply, category, sources, disclaimer } */
export async function sendChat({ message, sessionId }) {
  let response;
  try {
    response = await fetch(`${BASE}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId || null }),
    });
  } catch {
    throw new Error("Can't reach the server. Check that the backend is running.");
  }

  if (!response.ok) {
    if (response.status === 422) {
      throw new Error("That message couldn't be sent. Messages must be 1 to 2000 characters.");
    }
    throw new Error("The server hit a problem answering that. Try again in a moment.");
  }

  return response.json();
}

/** DELETE /chat/{session_id} - best effort, never throws */
export async function deleteChat(sessionId) {
  if (!sessionId) return;
  try {
    await fetch(`${BASE}/chat/${encodeURIComponent(sessionId)}`, { method: "DELETE" });
  } catch {
    /* the local chat is cleared either way */
  }
}
