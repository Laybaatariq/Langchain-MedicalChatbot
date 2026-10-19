import { useEffect, useRef, useState } from "react";
import { ChevronDownIcon } from "./Icons.jsx";

/**
 * The account area of the header.
 *   logged out: a "Log in" button
 *   logged in:  an avatar button (first letter of the name) that opens a small menu
 *               with "My appointments" and "Log out"
 */
export default function AccountMenu({ user, onLogin, onOpenAppointments, onLogout }) {
  const [open, setOpen] = useState(false);
  const boxRef = useRef(null);

  // Close the menu on a click outside it, or on Escape
  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event) => {
      if (boxRef.current && !boxRef.current.contains(event.target)) setOpen(false);
    };
    const onKeyDown = (event) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (!user) {
    return (
      <button type="button" className="ghost" onClick={onLogin}>
        Log in
      </button>
    );
  }

  const initial = (user.name || "?").trim().charAt(0).toUpperCase() || "?";
  const choose = (action) => () => {
    setOpen(false);
    action();
  };

  return (
    <div className="account-menu" ref={boxRef}>
      <button
        type="button"
        className="avatar-btn"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <span className="avatar-initial" aria-hidden="true">
          {initial}
        </span>
        <span className="account-name">{user.name}</span>
        <ChevronDownIcon />
      </button>

      {open && (
        <div className="menu" role="menu">
          <p className="menu-head">Signed in as {user.email}</p>
          <button type="button" role="menuitem" onClick={choose(onOpenAppointments)}>
            My appointments
          </button>
          <button type="button" role="menuitem" onClick={choose(onLogout)}>
            Log out
          </button>
        </div>
      )}
    </div>
  );
}