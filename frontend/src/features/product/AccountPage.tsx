import { Link } from "react-router-dom";
import { useEffect, useState } from "react";
import { useSession, type Account } from "./session";
import { currencies } from "../planning/currencies";
import { interestPrompts, pacePrompts, transportLabels, type Interest, type Pace, type Transport } from "./editor";
import type { Profile } from "./profile";
import "./account.css";
import "./editor.css";

export function AccountPage() {
  const { account, logout, status, refresh } = useSession();
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
        <span className="eyebrow">A LITTLE MORE YOU</span>
        <h1>Your account</h1>
        <p>The details that make every new journey feel familiar.</p>
      </div>
      <div className="account-layout"><aside className="content-card account-sidebar">
        <span className="avatar">{account.initials}</span>
        <h3>{account.display_name}</h3>
        <p>{account.email}</p>
        <Link to="/trips" className="text-link">My trips</Link><br /><br /><button
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
      </aside><ProfileForm key={account.id} account={account} refresh={refresh} logout={logout} /></div>
    </div>
  );
}

function ProfileForm({ account, refresh, logout }: { account: Account; refresh: () => Promise<void>; logout: () => Promise<void> }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    let active = true;
    fetch("/api/profile", { credentials: "same-origin", cache: "no-store" }).then(async response => {
      if (!response.ok) throw new Error("Profile unavailable");
      const value = await response.json();
      if (active) setProfile(value);
    }).catch(() => { if (active) setError("Your profile could not be loaded. Reload to try again."); });
    return () => { active = false; };
  }, []);
  function update(next: Profile) {
    const words = next.display_name.trim().split(/\s+/).filter(Boolean);
    const initials = (words.length > 1 ? [words[0], words[words.length - 1]] : words).map(word => word[0]).join("").toUpperCase();
    setProfile({ ...next, initials }); setSaved(false); setError("");
  }
  function toggle<T>(values: T[], value: T): T[] { return values.includes(value) ? values.filter(item => item !== value) : [...values, value]; }
  if (!profile) return <section className="content-card account-main"><p role={error ? "alert" : "status"}>{error || "Loading your profile…"}</p></section>;
  return <section className="content-card account-main brief-editor"><form onSubmit={event => {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setSaved(false); setError("");
    const body = { display_name: profile.display_name, currency: profile.currency, interests: profile.interests, pace: profile.pace, transport: profile.transport, notes: profile.notes };
    void fetch("/api/profile", { method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": account.csrf_token }, body: JSON.stringify(body) }).then(async response => {
      if (!response.ok) throw new Error("Update rejected");
      setProfile(await response.json()); setSaved(true);
      await refresh();
    }).catch(() => setError("Your changes could not be saved. Check your details and session, then try again.")).finally(() => setSaving(false));
  }}>
    <h2>Profile</h2>
    <div className="account-initials"><span className="avatar" aria-label={`Account initials: ${profile.initials}`}>{profile.initials}</span><p>Your initials are your account image.</p></div>
    <fieldset disabled={saving} className="profile-fields"><legend className="visually-hidden">Profile and travel defaults</legend>
      <div className="form-grid"><label className="field"><span>Display name</span><input value={profile.display_name} required maxLength={80} onChange={event => update({ ...profile, display_name: event.target.value })} /></label><label className="field"><span>Email address</span><input value={account.email} readOnly type="email" /></label></div>
      <section className="account-section"><h2>Travel defaults</h2><p className="subtle-help">A visible starting point for new travel briefs. Existing drafts and itineraries keep their own preferences.</p>
        <label className="field profile-currency"><span>Default currency</span><select value={profile.currency} onChange={event => update({ ...profile, currency: event.target.value })}>{currencies.map(value => <option key={value.code}>{value.code}</option>)}</select></label>
        <fieldset className="brief-choice-group"><legend>What are you drawn to?</legend><div className="interest-chips">{(Object.keys(interestPrompts) as Interest[]).map(value => <button key={value} type="button" className={`interest-chip ${profile.interests.includes(value) ? "selected" : ""}`} aria-pressed={profile.interests.includes(value)} onClick={() => update({ ...profile, interests: toggle(profile.interests, value) })}>{value}</button>)}</div></fieldset>
        <div className="preference-pair"><fieldset className="brief-choice-group"><legend>Travel pace</legend><div className="pace-row">{(Object.keys(pacePrompts) as Pace[]).map(value => <button key={value} type="button" className={`pace-btn ${profile.pace === value ? "selected" : ""}`} aria-pressed={profile.pace === value} onClick={() => update({ ...profile, pace: profile.pace === value ? null : value })}>{value[0].toUpperCase() + value.slice(1)}</button>)}</div><p className="selection-help">Choose one, or select again to clear.</p></fieldset>
        <fieldset className="brief-choice-group"><legend>Transport preferences</legend><div className="pace-row">{(Object.keys(transportLabels) as Transport[]).map(value => <button key={value} type="button" className={`pace-btn ${profile.transport.includes(value) ? "selected" : ""}`} aria-pressed={profile.transport.includes(value)} onClick={() => update({ ...profile, transport: toggle(profile.transport, value) })}>{transportLabels[value]}</button>)}</div><p className="selection-help">Soft priorities. Leave empty for no preference.</p></fieldset></div>
        <label className="field"><span>Additional preferences</span><textarea rows={4} maxLength={24000} value={profile.notes} onChange={event => update({ ...profile, notes: event.target.value })} placeholder="The little things you always like to keep in mind…" /></label>
      </section>
      <div className="profile-save-row"><span className="subtle-help">Changes apply to new travel briefs.</span><button type="submit" className="btn btn-primary">{saving ? "Saving…" : "Save changes"}</button></div>
    </fieldset>
    {saved && <p role="status">Your travel defaults have been saved.</p>}{error && <p role="alert">{error}</p>}
    <button type="button" className="btn btn-quiet account-mobile-logout" onClick={() => void logout().catch(() => setError("Could not end the server session. Please try logging in again."))}>Log out</button>
  </form></section>;
}
