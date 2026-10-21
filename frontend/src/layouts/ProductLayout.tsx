import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import { SessionProvider, useSession } from "../features/product/session";
import "../styles/dayloom.css";
import { TaskProvider, TaskEntry } from "../features/product/tasks";

export function ProductLayout() {
  return (
    <SessionProvider>
      <TaskProvider><ProductShell /></TaskProvider>
    </SessionProvider>
  );
}

function ProductShell() {
  const { account } = useSession();
  const [mobile, setMobile] = useState(false);
  return (
    <div className="dayloom">
      <header className="site-header">
        <div className="container nav-inner">
          <NavLink className="brand" to="/" aria-label="Dayloom home">
            <span className="brand-symbol" aria-hidden="true">
              ✧
            </span>
            <span className="brand-name">Dayloom</span>
          </NavLink>
          <nav className="site-nav" aria-label="Main navigation">
            <NavLink to="/" end>
              Home
            </NavLink>
            <NavLink to="/plan">Plan a trip</NavLink>
            <NavLink to="/trips">My trips</NavLink>
          </nav>
          <div className="nav-actions">
            <TaskEntry />
            {account ? (
              <NavLink
                to="/account"
                className="account-link"
                aria-label="Account settings"
              >
                <span className="avatar">{account.initials}</span>
                <span className="account-name">{account.display_name}</span>
              </NavLink>
            ) : (
              <NavLink to="/login" className="btn btn-quiet btn-small">
                Log in
              </NavLink>
            )}
            <NavLink to="/plan" className="btn btn-primary btn-small nav-cta">
              Start planning →
            </NavLink>
            <button
              type="button"
              className="mobile-toggle"
              aria-label="Open navigation"
              aria-expanded={mobile}
              onClick={() => setMobile(!mobile)}
            >
              ☰
            </button>
          </div>
        </div>
        {mobile && (
          <nav
            className="mobile-panel"
            aria-label="Mobile navigation"
            onClick={() => setMobile(false)}
          >
            <NavLink to="/">Home</NavLink>
            <NavLink to="/plan">Plan a trip</NavLink>
            <NavLink to="/trips">My trips</NavLink>
            <NavLink to={account ? "/account" : "/login"}>
              {account ? "Account settings" : "Log in"}
            </NavLink>
          </nav>
        )}
      </header>
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-flex">
          <div>
            <div className="footer-brand">✧ Dayloom</div>
            <p>Make room for the places that move you.</p>
          </div>
          <div className="footer-links">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/plan">Start planning</NavLink>
            <NavLink to="/trips">My trips</NavLink>
          </div>
        </div>
      </footer>
    </div>
  );
}
