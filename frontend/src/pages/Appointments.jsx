import { useCallback, useEffect, useState } from "react";
import { cancelAppointment, listMyAppointments } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";

/** "Wed 14 Oct, 10:30" (clinic time, from the server) -> its parts, or null if it looks different */
function parseLabel(label) {
  const match = /^(\w{3}) (\d{1,2}) (\w{3}), (\d{1,2}:\d{2})$/.exec(label || "");
  return match ? { weekday: match[1], day: match[2], month: match[3], time: match[4] } : null;
}

function Row({ appointment, onCancel, busy }) {
  const parts = parseLabel(appointment.start_label);
  const cancelled = appointment.status === "cancelled";

  return (
    <li className={`appt${cancelled ? " is-cancelled" : ""}`}>
      {parts && (
        <span className="appt-date" aria-hidden="true">
          <span className="day">{parts.day}</span>
          <span className="month">
            {parts.weekday} · {parts.month}
          </span>
        </span>
      )}
      <div className="appt-main">
        <p className="appt-when">
          <span className="visually-hidden">{appointment.start_label}. </span>
          {parts ? `${parts.time}, ` : `${appointment.start_label}, `}
          {appointment.duration_minutes} minutes
        </p>
        <p className="appt-who">
          {appointment.doctor_name} · {appointment.specialty}
        </p>
        {appointment.summary_shared && <p className="muted small">Symptom summary shared with the doctor</p>}
      </div>
      <div className="appt-side">
        <span className={`status status-${appointment.status}`}>{appointment.status}</span>
        {appointment.can_cancel && (
          <button type="button" className="link danger" disabled={busy} onClick={() => onCancel(appointment)}>
            Cancel
          </button>
        )}
      </div>
    </li>
  );
}

/** The patient's own appointments. onLogin opens the log in dialog. */
export default function Appointments({ onLogin }) {
  const { user, ready } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await listMyAppointments());
      setError(null);
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => {
    if (user) load();
    else setData(null);
  }, [user, load]);

  async function cancel(appointment) {
    if (!window.confirm(`Cancel your appointment on ${appointment.start_label}?`)) return;
    setBusy(true);
    try {
      await cancelAppointment(appointment.id);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (!ready) return null;

  if (!user) {
    return (
      <section className="page">
        <h2>My appointments</h2>
        <p className="muted">Please log in to see your appointments.</p>
        <button type="button" className="primary" onClick={onLogin}>
          Log in
        </button>
      </section>
    );
  }

  return (
    <section className="page">
      <h2>My appointments</h2>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      {!data && !error && <p className="muted">Loading...</p>}

      {data && (
        <>
          <h3>Upcoming</h3>
          {data.upcoming.length === 0 ? (
            <p className="muted">No upcoming appointments. Describe your symptoms in the chat to find a doctor.</p>
          ) : (
            <ul className="appt-list">
              {data.upcoming.map((a) => (
                <Row key={a.id} appointment={a} onCancel={cancel} busy={busy} />
              ))}
            </ul>
          )}

          {data.past.length > 0 && (
            <>
              <h3>Past and cancelled</h3>
              <ul className="appt-list">
                {data.past.map((a) => (
                  <Row key={a.id} appointment={a} onCancel={cancel} busy={busy} />
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}