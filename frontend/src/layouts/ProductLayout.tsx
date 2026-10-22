import { isDialogBackdropClick } from '../shared/dialog';
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { SessionProvider, useSession } from "../features/product/session";
import "../styles/dayloom.css";
import { TaskProvider, TaskEntry } from "../features/product/tasks";
import { Icon } from "../features/product/Icon";

export function ProductLayout() {
  return (
    <SessionProvider>
      <TaskProvider><ProductShell /></TaskProvider>
    </SessionProvider>
  );
}

function ProductShell() {
  const { account, logout } = useSession();
  const { pathname } = useLocation();
  const librarySelected = pathname === "/trips" || pathname === "/import" ||
    ["/trips/", "/drafts/", "/examples/", "/previews/"].some(prefix => pathname.startsWith(prefix));
  const [mobile, setMobile] = useState(false);
  const [about, setAbout] = useState(false);
  const [navigationError, setNavigationError] = useState("");
  const aboutDialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const dialog = aboutDialog.current;
    if (!about || !dialog) return;
    const opener = document.activeElement;
    dialog.showModal();
    return () => {
      dialog.close();
      if (opener instanceof HTMLElement && opener.isConnected) opener.focus();
    };
  }, [about]);
  return (
    <div className="dayloom">
      <header className="site-header">
        <div className="container nav-inner">
          <NavLink className="brand" to="/" aria-label="Dayloom home">
            <span className="brand-symbol" aria-hidden="true">
              <Icon name="spark" size={21} />
            </span>
            <span className="brand-name">Dayloom</span>
          </NavLink>
          <nav className="site-nav" aria-label="Main navigation">
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "selected" : ""}`}>
              Home
            </NavLink>
            <NavLink to="/plan" className={({ isActive }) => `nav-link ${isActive ? "selected" : ""}`}>Plan a trip</NavLink>
            <Link to="/trips" className={`nav-link ${librarySelected ? "selected" : ""}`} aria-current={librarySelected ? "page" : undefined}>My trips</Link>
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
              Start planning <Icon name="arrow" size={16} />
            </NavLink>
            <button
              type="button"
              className="mobile-toggle"
              aria-label="Open navigation"
              aria-expanded={mobile}
              onClick={() => setMobile(!mobile)}
            >
              <Icon name="menu" size={23} />
            </button>
          </div>
        </div>
        {mobile && (
          <nav
            className="mobile-panel"
            aria-label="Mobile navigation"
            onClick={() => setMobile(false)}
          >
            <NavLink to="/" end className={({ isActive }) => `nav-link ${isActive ? "selected" : ""}`}>Home</NavLink>
            <NavLink to="/plan" className={({ isActive }) => `nav-link ${isActive ? "selected" : ""}`}>Plan a trip</NavLink>
            <Link to="/trips" className={`nav-link ${librarySelected ? "selected" : ""}`} aria-current={librarySelected ? "page" : undefined}>My trips</Link>
            <NavLink to={account ? "/account" : "/login"} className={({ isActive }) => `nav-link ${isActive ? "selected" : ""}`}>
              {account ? "Account settings" : "Log in"}
            </NavLink>
            {account && <button type="button" className="btn btn-quiet btn-small" onClick={() => void logout().catch(() => setNavigationError("Could not end the server session. Please try logging in again."))}>Log out</button>}
          </nav>
        )}
      </header>
      {navigationError && <p role="alert" className="container form-error">{navigationError}</p>}
      <main>
        <Outlet />
      </main>
      <footer className="site-footer">
        <div className="container footer-flex">
          <div>
            <div className="footer-brand"><Icon name="spark" size={21} /> Dayloom</div>
            <p>Make room for the places that move you.</p>
          </div>
          <div className="footer-links">
            <NavLink to="/">Home</NavLink>
            <NavLink to="/plan">Start planning</NavLink>
            <NavLink to="/trips">My trips</NavLink>
            <NavLink to={account ? "/account" : "/login"}>My account</NavLink>
          </div>
        </div>
        <div className="container footer-note">
          Thoughtful city itineraries, made yours. Confirm travel details before you go.{" "}
          <button type="button" className="inline-action" onClick={() => setAbout(true)}>About Dayloom</button>
        </div>
      </footer>
      {about && <dialog ref={aboutDialog} className="modal-card wide-modal about-dialog" aria-labelledby="about-dayloom-title" onCancel={() => setAbout(false)} onClick={event => {
        if (isDialogBackdropClick(event)) setAbout(false);
      }}>
        <button type="button" className="modal-close" aria-label="Close About Dayloom" onClick={() => setAbout(false)}><Icon name="close" size={21} /></button>
        <div className="modal-icon"><Icon name="spark" size={23} /></div>
        <h2 id="about-dayloom-title">Dayloom</h2>
        <p>A destination, a few ideas, a rhythm that feels like you. Bring your days together in one clear itinerary.</p>
        <div className="detail-note"><strong>Your travel ideas</strong><span>Keep unfinished briefs, save itineraries, and return to your own collection.</span></div>
        <div className="detail-note"><strong>Planning &amp; recovery</strong><span>Your confirmed brief guides each planning task. You can return to its progress, then save or discard the preview when it is ready.</span></div>
        <div className="detail-note"><strong>Travel details</strong><span>Check opening times, weather, connections and booking requirements before you go. Unconfirmed information stays visible.</span></div>
        <div className="detail-note"><strong>Images</strong><span>Destination and atmosphere images offer inspiration. Illustrations are labeled, and place photographs show their source when available.</span></div>
        <div className="modal-actions"><button type="button" className="btn btn-primary" onClick={() => setAbout(false)}>Continue exploring</button></div>
      </dialog>}
    </div>
  );
}
