/**
 * Doctor suggestions under an intake result.
 * onBook(doctor) opens the booking dialog; without it the cards have no Book button.
 */
export default function DoctorCards({ doctors, onBook }) {
  if (!doctors?.length) return null;

  const hasSample = doctors.some((d) => d.is_sample);

  return (
    <section className="doctors" aria-label="Suggested doctors">
      <h3>Doctors you can see</h3>
      <ul>
        {doctors.map((d) => (
          <li key={d.id} className="doctor">
            <div className="doctor-head">
              <p className="doctor-name">{d.name}</p>
              <span className="doctor-tag">{d.specialty}</span>
            </div>
            <p className="doctor-meta">
              {d.city} · {d.experience_years} years of experience · PKR {Number(d.fee_pkr).toLocaleString()}
            </p>
            <p className="doctor-meta">
              {d.modes.join(" or ")} · {d.days.join(", ")}
            </p>
            {onBook && (
              <button type="button" className="book-button" onClick={() => onBook(d)}>
                Book appointment
              </button>
            )}
          </li>
        ))}
      </ul>
      {hasSample && <p className="doctor-note">Sample data: these doctors are fictional.</p>}
    </section>
  );
}