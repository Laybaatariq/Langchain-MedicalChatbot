import { useCallback, useEffect, useState } from "react";
import { bookAppointment, getSlots } from "../api.js";
import { useAuth } from "../auth/AuthContext.jsx";
import AuthForm from "./AuthForm.jsx";
import Modal from "./Modal.jsx";

/**
 * Book an appointment with one doctor.
 *   not logged in -> log in / sign up first
 *   logged in     -> pick a day and a time, optionally share the symptom summary, confirm
 * sessionId is the chat session, so the backend can find the finished symptom intake.
 */
export default function BookingDialog({ doctor, sessionId, onClose }) {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [dayIndex, setDayIndex] = useState(0);
  const [slot, setSlot] = useState(null);
  const [share, setShare] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [booked, setBooked] = useState(null);

  const loadSlots = useCallback(async () => {
    try {
      setData(await getSlots(doctor.id));
      setLoadError(null);
      setDayIndex(0);
      setSlot(null);
    } catch (err) {
      setLoadError(err.message);
    }
  }, [doctor.id]);

  useEffect(() => {
    if (user) loadSlots();
  }, [user, loadSlots]);

  async function confirm() {
    if (!slot) return;
    setBusy(true);
    setError(null);
    try {
      setBooked(await bookAppointment({ doctorId: doctor.id, start: slot.start, shareSummary: share, sessionId }));
    } catch (err) {
      setError(err.message);
      if (err.status === 409) loadSlots(); // somebody took it: show the fresh list
    } finally {
      setBusy(false);
    }
  }

  // ---- 1. confirmation
  if (booked) {
    return (
      <Modal title="Appointment confirmed" onClose={onClose}>
        <div className="booked">
          <p className="booked-when">{booked.start_label}</p>
          <p>
            {booked.doctor_name} · {booked.specialty}
          </p>
          <p className="muted">
            {booked.summary_shared
              ? "Your symptom summary will be visible to the doctor."
              : "Your symptom summary was not shared."}
          </p>
          <p className="muted">This is a demo: no email or message is sent, and the doctor is fictional.</p>
          <button type="button" className="primary" onClick={onClose}>
            Done
          </button>
        </div>
      </Modal>
    );
  }

  // ---- 2. log in first
  if (!user) {
    return (
      <Modal title={`Book ${doctor.name}`} onClose={onClose}>
        <p className="muted">Please log in or create an account to book an appointment.</p>
        <AuthForm />
      </Modal>
    );
  }

  // ---- 3. pick a time
  const day = data?.days?.[dayIndex];

  return (
    <Modal title={`Book ${doctor.name}`} onClose={onClose}>
      <p className="muted">
        {doctor.specialty} · {doctor.city} · PKR {Number(doctor.fee_pkr).toLocaleString()}
      </p>

      {loadError && (
        <p className="form-error" role="alert">
          {loadError}
        </p>
      )}
      {!data && !loadError && <p className="muted">Loading free times...</p>}
      {data && data.days.length === 0 && <p>No free times in the next 7 days.</p>}

      {data && data.days.length > 0 && (
        <>
          <div className="day-tabs" role="tablist" aria-label="Day">
            {data.days.map((d, i) => (
              <button
                key={d.date}
                type="button"
                role="tab"
                aria-selected={i === dayIndex}
                className="day-tab"
                onClick={() => {
                  setDayIndex(i);
                  setSlot(null);
                }}
              >
                {d.label}
              </button>
            ))}
          </div>

          <div className="slots" role="group" aria-label="Times">
            {day.slots.map((s) => (
              <button
                key={s.start}
                type="button"
                className="slot"
                aria-pressed={slot?.start === s.start}
                onClick={() => setSlot(s)}
              >
                {s.label}
              </button>
            ))}
          </div>
          <p className="muted small">Times are in {data.timezone} time. Each visit is 30 minutes.</p>

          {sessionId && (
            <label className="check">
              <input type="checkbox" checked={share} onChange={(e) => setShare(e.target.checked)} />
              Share my symptom summary with the doctor
            </label>
          )}

          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}

          <button type="button" className="primary" disabled={!slot || busy} onClick={confirm}>
            {busy ? "Booking..." : slot ? `Confirm ${day.label}, ${slot.label}` : "Pick a time"}
          </button>
        </>
      )}
    </Modal>
  );
}