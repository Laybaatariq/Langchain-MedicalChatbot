export default function DoctorCards({ doctors }) {
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
          </li>
        ))}
      </ul>
      {hasSample && <p className="doctor-note">Sample data: these doctors are fictional.</p>}
    </section>
  );
}