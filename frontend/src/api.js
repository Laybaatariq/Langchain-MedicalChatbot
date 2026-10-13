// Empty in development: requests go to the Vite dev server, which proxies them to the backend.
// For a deployed frontend, set VITE_API_URL to the backend URL (e.g. https://my-api.example.com).
const BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

const TOKEN_KEY = "medchat:token";

export const getToken = () => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const setToken = (token) => {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable: the login just will not survive a refresh */
  }
};

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

const FALLBACK_MESSAGES = {
  401: "Please log in.",
  404: "That was not found.",
  409: "That conflicts with an existing booking.",
  422: "Please check what you entered.",
};

/** Calls the backend and returns the JSON. Throws ApiError with a readable message. */
async function request(method, path, body, { auth = false } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = auth ? getToken() : null;
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  try {
    response = await fetch(`${BASE}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("Can't reach the server. Check that the backend is running.", 0);
  }

  if (!response.ok) {
    let detail = null;
    try {
      const data = await response.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* no JSON body */
    }
    if (response.status === 401 && token) {
      // the saved login is no longer valid (expired or removed)
      setToken(null);
      window.dispatchEvent(new Event("medchat:logout"));
    }
    throw new ApiError(
      detail || FALLBACK_MESSAGES[response.status] || "The server hit a problem. Try again in a moment.",
      response.status
    );
  }
  return response.json();
}

// ---------------------------------------------------------------- chat
/** POST /chat -> { session_id, reply, category, sources, disclaimer, ... } */
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

// ---------------------------------------------------------------- accounts
export const signup = (name, email, password) => request("POST", "/auth/signup", { name, email, password });
export const login = (email, password) => request("POST", "/auth/login", { email, password });
export const getMe = () => request("GET", "/auth/me", undefined, { auth: true });

// ---------------------------------------------------------------- booking
export const getSlots = (doctorId) => request("GET", `/doctors/${encodeURIComponent(doctorId)}/slots`);

export const bookAppointment = ({ doctorId, start, shareSummary, sessionId }) =>
  request(
    "POST",
    "/appointments",
    { doctor_id: doctorId, start, share_summary: shareSummary, session_id: sessionId || null },
    { auth: true }
  );

export const listMyAppointments = () => request("GET", "/appointments/me", undefined, { auth: true });

export const cancelAppointment = (appointmentId) =>
  request("POST", `/appointments/${encodeURIComponent(appointmentId)}/cancel`, undefined, { auth: true });