import { Link } from "react-router-dom";
import { useState } from "react";
import { useSession } from "./session";

export function AccountPage() {
  const { account, logout, status } = useSession();
  const [error, setError] = useState("");
  if (!account)
    return (
      <div className="page container">
        <h1>
          {status === "loading" ? "Checking your session…" : "Your account"}
        </h1>
        <Link to="/login?return=/account">Log in</Link>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  return (
    <div className="page container">
      <div className="page-heading">
        <span className="eyebrow">YOUR DAYLOOM</span>
        <h1>Account settings</h1>
        <p>Your plans and preferences, together.</p>
      </div>
      <section className="flow-card">
        <span className="avatar">{account.initials}</span>
        <h2>{account.display_name}</h2>
        <p>{account.email}</p>
        <button
          className="btn btn-light"
          onClick={() => {
            void logout().catch(() =>
              setError(
                "Could not end the server session. Please try logging in again.",
              ),
            );
          }}
        >
          Log out
        </button>
        {error && <p role="alert">{error}</p>}
      </section>
    </div>
  );
}
