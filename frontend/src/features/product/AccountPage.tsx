import { Link } from "react-router-dom";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSession, type Account } from "./session";
import { currencies } from "../planning/currencies";
import { interestPrompts, pacePrompts, transportLabels, type Interest, type Pace, type Transport } from "./editor";
import type { Profile } from "./profile";
import { Icon } from "./Icon";
import "./account.css";
import { AccountDeletion } from "./AccountDeletion";

type AccountPreview = Pick<Profile, "display_name" | "initials">;

export function AccountPage() {
  const { account, logout, status, refresh, deleteAccount } = useSession();
  const [deleted, setDeleted] = useState(false);
  const [logoutError, setLogoutError] = useState<{ owner: string; session: string; message: string } | null>(null);
  const error = logoutError && (!account || (account.id === logoutError.owner && account.csrf_token === logoutError.session)) ? logoutError.message : "";
  const [preview, setPreview] = useState<{ owner: string; profile: AccountPreview } | null>(null);
  const previewProfile = useCallback((profile: AccountPreview) => setPreview({ owner: account?.id || "", profile }), [account?.id]);
  const accountNow = useRef(account);
  accountNow.current = account;
  const mounted = useRef(false);
  const logoutAttempt = useRef(0);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  async function handleLogout() {
    const owner = accountNow.current;
    if (!owner) return;
    const attempt = ++logoutAttempt.current;
    setLogoutError(null);
    try {
      await logout();
    } catch {
      const current = accountNow.current;
      if (mounted.current && logoutAttempt.current === attempt && (!current || (current.id === owner.id && current.csrf_token === owner.csrf_token))) {
        setLogoutError({ owner: owner.id, session: owner.csrf_token, message: "Could not end the server session. Please try logging in again." });
      }
    }
  }
  async function handleDelete(password: string) {
    const owner = accountNow.current;
    await deleteAccount(password);
    const current = accountNow.current;
    if (mounted.current && (!current || (current.id === owner?.id && current.csrf_token === owner.csrf_token))) setDeleted(true);
  }
  if (!account)
    return (
      <div className="page container">
        <h1>
          {status === "loading" ? "Checking your session…" : "Your account"}
        </h1>
        {deleted && <p role="status">Your account and its travel data have been deleted.</p>}
        <Link to="/login?return=/account">Log in</Link>
        {error && <p role="alert">{error}</p>}
      </div>
    );
  const visual = preview?.owner === account.id ? preview.profile : account;
  return (
    <div className="page container">
      <div className="page-heading">
        <span className="eyebrow">A LITTLE MORE YOU</span>
        <h1>Your account</h1>
        <p>The details that make every new journey feel familiar.</p>
      </div>
      <div className="account-layout"><aside className="content-card account-sidebar">
        <span className="avatar large">{visual.initials}</span>
        <h3>{visual.display_name}</h3>
        <p className="small-muted">{account.email}</p>
        <hr className="account-divider" />
        <Link to="/trips" className="text-link">My trips</Link><br /><br /><button
          className="inline-action text-danger"
          onClick={() => void handleLogout()}
        >
          Log out
        </button>
        {error && <p role="alert">{error}</p>}
      </aside><ProfileForm key={`${account.id}:${account.csrf_token}`} account={account} refresh={refresh} logout={handleLogout} onDelete={handleDelete} onPreview={previewProfile} /></div>
    </div>
  );
}

function ProfileForm({ account, refresh, logout, onPreview, onDelete }: { account: Account; refresh: () => Promise<void>; logout: () => Promise<void>; onPreview: (profile: AccountPreview) => void; onDelete: (password: string) => Promise<void> }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    let active = true;
    fetch("/api/profile", { credentials: "same-origin", cache: "no-store" }).then(async response => {
      if (!active) return;
      if (response.status === 401) { await refresh(); return; }
      if (!response.ok) throw new Error("Profile unavailable");
      const value = await response.json();
      if (active) { setProfile(value); onPreview(value); }
    }).catch(() => { if (active) setError("Your profile could not be loaded. Reload to try again."); });
    return () => { active = false; mounted.current = false; };
  }, [refresh, onPreview]);
  function update(next: Profile) {
    const words = next.display_name.trim().split(/\s+/).filter(Boolean);
    const initials = (words.length > 1 ? [words[0], words[words.length - 1]] : words).map(word => word[0]).join("").toUpperCase();
    const value = { ...next, initials };
    setProfile(value); onPreview(value); setSaved(false); setError("");
  }
  function toggle<T>(values: T[], value: T): T[] { return values.includes(value) ? values.filter(item => item !== value) : [...values, value]; }
  if (!profile) return <section className="content-card account-main"><p role={error ? "alert" : "status"}>{error || "Loading your profile…"}</p></section>;
  return <section className="content-card account-main"><form onSubmit={event => {
    event.preventDefault();
    if (saving) return;
    setSaving(true); setSaved(false); setError("");
    const body = { display_name: profile.display_name, currency: profile.currency, interests: profile.interests, pace: profile.pace, transport: profile.transport, notes: profile.notes };
    void fetch("/api/profile", { method: "PUT", credentials: "same-origin", headers: { "Content-Type": "application/json", "X-CSRF-Token": account.csrf_token }, body: JSON.stringify(body) }).then(async response => {
      if (!mounted.current) return;
      if (response.status === 401) { await refresh(); return; }
      if (!response.ok) throw new Error("Update rejected");
      const value = await response.json();
      if (!mounted.current) return;
      setProfile(value); onPreview(value); setSaved(true);
      await refresh();
    }).catch(() => { if (mounted.current) setError("Your changes could not be saved. Check your details and session, then try again."); }).finally(() => { if (mounted.current) setSaving(false); });
  }}>
    <h2>Profile</h2>
    <div className="avatar-tools"><span className="avatar large" aria-label={`Account initials: ${profile.initials}`}>{profile.initials}</span><p className="small-muted">Your initials are your account image.</p></div>
    <fieldset disabled={saving} className="profile-fields"><legend className="visually-hidden">Profile and travel defaults</legend>
      <div className="form-grid"><label className="field"><span>Display name</span><input value={profile.display_name} required maxLength={80} onChange={event => update({ ...profile, display_name: event.target.value })} /></label><label className="field"><span>Email address</span><input value={account.email} readOnly type="email" /></label></div>
      <section className="account-section"><h2>Travel defaults</h2><p className="small-muted">A visible starting point for new travel briefs. Existing drafts and itineraries keep their own preferences.</p>
        <label className="field profile-currency"><span>Default currency</span><select value={profile.currency} onChange={event => update({ ...profile, currency: event.target.value })}>{currencies.map(value => <option key={value.code}>{value.code}</option>)}</select></label>
        <fieldset className="field-group"><legend className="label-row"><Icon name="spark" size={16} /><strong>Experiences you love</strong></legend><div className="chips">{(Object.keys(interestPrompts) as Interest[]).map(value => <button key={value} type="button" className={`chip ${profile.interests.includes(value) ? "active" : ""}`} aria-pressed={profile.interests.includes(value)} onClick={() => update({ ...profile, interests: toggle(profile.interests, value) })}><Icon name={profile.interests.includes(value) ? "check" : "plus"} size={14} /> {value}</button>)}</div></fieldset>
        <div className="preference-pair"><fieldset className="field-group"><legend className="label-row"><Icon name="sliders" size={16} /><strong>Travel pace</strong></legend><div className="pace-row">{(Object.keys(pacePrompts) as Pace[]).map((value, index) => <button key={value} type="button" className={`pace-btn ${profile.pace === value ? "selected" : ""}`} aria-label={value[0].toUpperCase() + value.slice(1)} aria-pressed={profile.pace === value} onClick={() => update({ ...profile, pace: profile.pace === value ? null : value })}><span>{["Take it slowly", "A little of both", "See a little more"][index]}</span><strong>{value[0].toUpperCase() + value.slice(1)}</strong></button>)}</div></fieldset>
        <fieldset className="field-group transport-selection"><legend className="label-row"><Icon name="route" size={16} /><strong>Transport preferences</strong></legend><div className="pace-row">{(Object.keys(transportLabels) as Transport[]).map((value, index) => <button key={value} type="button" className={`pace-btn ${profile.transport.includes(value) ? "selected" : ""}`} aria-pressed={profile.transport.includes(value)} onClick={() => update({ ...profile, transport: toggle(profile.transport, value) })}><span><Icon name={["walk", "bus", "car"][index]} size={17} /></span><strong>{transportLabels[value]}</strong></button>)}</div></fieldset></div>
      </section>
      <div className="profile-save-row"><span className="small-muted">Changes apply to new travel briefs.</span><button type="submit" className="btn btn-primary">{saving ? "Saving…" : "Save changes"} <Icon name="check" size={16} /></button></div>
    </fieldset>
    {saved && <p role="status">Your travel defaults have been saved.</p>}{error && <p role="alert">{error}</p>}
    <div className="quiet-links account-logout"><button type="button" className="inline-action text-danger" onClick={() => void logout()}>Log out</button></div>
  </form><AccountDeletion allowed={profile.can_delete_account === true} onDelete={onDelete} /></section>;
}
