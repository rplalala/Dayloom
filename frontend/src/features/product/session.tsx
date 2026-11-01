import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createBrief, restoreBrief, type Brief } from "./editor";
import { briefFromProfile } from "./profile";
import { invalidatePhotos } from './detail/photoSession';
import { forgetOwnerCopyIntents } from './copyIntents';
import { useExpiredGuestBrief } from './useExpiredGuestBrief';
export type { Brief } from "./editor";

export type Account = {
  id: string;
  email: string;
  display_name: string;
  initials: string;
  csrf_token: string;
};
export const emptyBrief: Brief = createBrief();
type Recovery = {
  owner: string | null;
  brief: Brief;
  actionId: string | null;
  generation?: string;
  origin?: BriefOrigin;
  defaultsAttempted?: boolean;
  started?: boolean;
  draftRef?: DraftRef | null;
  draftTitle?: string;
};
export type BriefOrigin = "new" | "edited" | "restored" | "draft" | "replan";
export type DraftRef = { id: string; title: string; revision: number };
const key = "dayloom.editor.v1";
const previousKey = 'dayloom.editor.previous.v1';
const noticeKey = "dayloom.account.notice";
const activeKey = "dayloom.account.active";
const logoutKey = "dayloom.account.logged-out";
const invalidationPrefix = "dayloom.account.invalidation.";

function activeLogin(): { id: string; nonce: string } | null {
  try {
    const saved = JSON.parse(localStorage.getItem(activeKey) || "null");
    return saved &&
      typeof saved.id === "string" &&
      typeof saved.nonce === "string"
      ? saved
      : null;
  } catch {
    return null;
  }
}

function generation(owner: string): string {
  try {
    return localStorage.getItem(invalidationPrefix + owner) || "";
  } catch {
    return "";
  }
}

function invalidate(owner: string | null) {
  if (!owner) return;
  invalidatePhotos({ owner });
  try {
    localStorage.setItem(invalidationPrefix + owner, crypto.randomUUID());
    forgetOwnerCopyIntents(owner);
    const intent = JSON.parse(sessionStorage.getItem('dayloom.task.intent.v1') || 'null');
    if (intent?.owner === owner) sessionStorage.removeItem('dayloom.task.intent.v1');
    const importIntent = JSON.parse(sessionStorage.getItem('dayloom.import.intent.v1') || 'null');
    if (importIntent?.owner === owner) sessionStorage.removeItem('dayloom.import.intent.v1');
  } catch {
    /* Keep this tab cleared. */
  }
}

function blockCurrentSession() {
  try {
    sessionStorage.setItem(logoutKey, activeLogin()?.nonce || "");
  } catch {
    /* In-flight fencing remains in memory. */
  }
}

function sessionBlocked(): boolean {
  try {
    const marker = sessionStorage.getItem(logoutKey);
    return marker !== null && marker === (activeLogin()?.nonce || "");
  } catch {
    return false;
  }
}

function beginLogin(next: Account) {
  invalidatePhotos({ privateOnly: true });
  const previous = activeLogin();
  if (previous && previous.id !== next.id) invalidate(previous.id);
  try {
    localStorage.setItem(
      activeKey,
      JSON.stringify({ id: next.id, nonce: crypto.randomUUID() }),
    );
    sessionStorage.removeItem(logoutKey);
  } catch {
    /* A successful explicit login is also fenced in memory. */
  }
}
function notify(value: object) {
  try {
    localStorage.setItem(
      noticeKey,
      JSON.stringify({ ...value, nonce: crypto.randomUUID() }),
    );
  } catch {
    /* Server revocation remains authoritative. */
  }
}
type Session = {
  account: Account | null;
  status: "loading" | "guest" | "authenticated" | "expired";
  brief: Brief;
  briefOrigin: BriefOrigin;
  defaultsApplied: boolean;
  initializeNewBrief: () => Promise<void>;
  newBrief: () => void;
  replaceBrief: (brief: Brief, origin: "draft" | "replan" | "restored") => void;
  draftRef: DraftRef | null;
  draftTitle: string;
  setDraftTitle: (value: string) => void;
  setDraftRef: (value: DraftRef | null) => void;
  actionId: string | null;
  editBrief: (brief: Brief) => void;
  setActionId: (id: string | null) => void;
  authenticate: (
    mode: "login" | "register",
    data: Record<string, string>,
  ) => Promise<void>;
  logout: () => Promise<void>;
  deleteAccount: (password: string) => Promise<void>;
  refresh: () => Promise<void>;
  hasPreviousBrief?: boolean;
  restorePreviousBrief?: () => void;
};
const SessionContext = createContext<Session | null>(null);

function readRecovery(storageKey = key): Recovery {
  try {
    const saved = JSON.parse(sessionStorage.getItem(storageKey) || "null");
    if (
      saved &&
      typeof saved === "object" &&
      saved.brief &&
      ["destination", "start_date", "end_date", "travelers", "budget", "currency", "preferences"].every(
        (k) => typeof saved.brief[k] === "string",
      ) &&
      (saved.owner === null || typeof saved.owner === "string") &&
      (saved.actionId === null || typeof saved.actionId === "string")
    ) {
      if (saved.owner && (saved.generation || "") !== generation(saved.owner)) {
        return { owner: null, brief: { ...emptyBrief }, actionId: null, origin: "new", started: false };
      }
      const unopened = saved.origin === "new" && saved.started === false && !saved.defaultsAttempted;
      const draftRef = saved.draftRef && typeof saved.draftRef.id === "string" && typeof saved.draftRef.title === "string" && Number.isSafeInteger(saved.draftRef.revision) && saved.draftRef.revision > 0 ? saved.draftRef as DraftRef : null;
      const draftTitle = typeof saved.draftTitle === "string" && saved.draftTitle.length <= 120 ? saved.draftTitle : draftRef?.title || "";
      return { ...saved, brief: restoreBrief(saved.brief), origin: unopened ? "new" : "restored", defaultsAttempted: unopened ? false : true, draftRef, draftTitle };
    }
  } catch {
    /* An unavailable storage area must not prevent planning. */
  }
  return { owner: null, brief: { ...emptyBrief }, actionId: null, origin: "new", started: false };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const recovery = useRef<Recovery>(readRecovery());
  const guest = useExpiredGuestBrief(JSON.stringify([recovery.current.owner, recovery.current.owner ? generation(recovery.current.owner) : '']));
  const clearGuest = guest.clear;
  const previousRecovery = useRef<Recovery | null>(readRecovery(previousKey));
  const [previousAvailable, setPreviousAvailable] = useState(Boolean(previousRecovery.current?.owner));
  const rememberPrevious = useCallback((value: Recovery | null) => {
    previousRecovery.current = value; setPreviousAvailable(Boolean(value?.owner));
    try {
      if (value?.owner) sessionStorage.setItem(previousKey, JSON.stringify(value));
      else sessionStorage.removeItem(previousKey);
    } catch { /* Recovery stays in memory when storage is unavailable. */ }
  }, []);
  const accountRef = useRef<Account | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [status, setStatus] = useState<Session["status"]>("loading");
  const [brief, setBrief] = useState<Brief>({ ...emptyBrief });
  const [actionId, setAction] = useState<string | null>(null);
  const [briefOrigin, setBriefOrigin] = useState<BriefOrigin>(recovery.current.origin || "new");
  const [defaultsApplied, setDefaultsApplied] = useState(false);
  const [draftRef, setDraft] = useState<DraftRef | null>(null);
  const [draftTitle, setTitle] = useState("");
  const briefRevision = useRef(0);
  const epoch = useRef(0);
  const loggingOut = useRef(false);

  const persist = useCallback(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(recovery.current));
    } catch {
      /* Memory remains usable. */
    }
  }, []);
  const clear = useCallback(() => {
    clearGuest();
    rememberPrevious(null);
    invalidatePhotos({ privateOnly: true });
    try { sessionStorage.removeItem('dayloom.task.intent.v1'); } catch { /* Account content stays hidden in memory. */ }
    try { sessionStorage.removeItem('dayloom.copy.intent.v1'); } catch { /* Invalidation also fences recovery. */ }
    recovery.current = {
      owner: null,
      brief: { ...emptyBrief },
      actionId: null,
      origin: "new",
      started: false,
    };
    accountRef.current = null;
    setAccount(null);
    setBrief({ ...emptyBrief });
    setAction(null);
    briefRevision.current++;
    setBriefOrigin("new");
    setDefaultsApplied(false);
    setDraft(null);
    setTitle("");
    setStatus("guest");
    persist();
  }, [persist, clearGuest, rememberPrevious]);
  const adopt = useCallback(
    (next: Account) => {
      if (loggingOut.current || sessionBlocked()) return;
      const previousOwner = accountRef.current?.id || recovery.current.owner || activeLogin()?.id;
      if (previousRecovery.current?.owner !== next.id) rememberPrevious(null);
      if (previousOwner && previousOwner !== next.id) invalidatePhotos({ owner: previousOwner });
      if (
        recovery.current.owner &&
        (recovery.current.owner !== next.id ||
          (recovery.current.generation || "") !==
            generation(recovery.current.owner))
      ) {
        briefRevision.current++;
        setDefaultsApplied(false);
        recovery.current = {
          owner: next.id,
          brief: { ...emptyBrief },
          actionId: null,
          generation: generation(next.id),
          origin: "new",
          started: false,
        };
      } else {
        recovery.current.owner = next.id;
        recovery.current.generation = generation(next.id);
      }
      accountRef.current = next;
      setAccount(next);
      setStatus("authenticated");
      setBrief({ ...recovery.current.brief });
      setAction(recovery.current.actionId);
      setBriefOrigin(recovery.current.origin || "new");
      setDraft(recovery.current.draftRef || null);
      setTitle(recovery.current.draftTitle || "");
      persist();
    },
    [persist, rememberPrevious],
  );

  const refresh = useCallback(async () => {
    if (loggingOut.current) return;
    if (sessionBlocked()) {
      if (recovery.current.owner) clear();
      else {
        setStatus("guest");
        setBrief({ ...recovery.current.brief });
        setAction(recovery.current.actionId);
        setTitle(recovery.current.draftTitle || "");
      }
      return;
    }
    const version = ++epoch.current;
    try {
      const response = await fetch("/api/auth/current", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const body = await response.json();
      if (version !== epoch.current || loggingOut.current || sessionBlocked())
        return;
      if (response.ok) {
        adopt(body);
        return;
      }
      if (response.status !== 401) throw new Error("Session unavailable");
      invalidatePhotos({ privateOnly: true });
      if (
        [
          "session_revoked",
          "invalid_session",
          "conflicting_credentials",
        ].includes(body.detail?.code)
      ) {
        invalidate(recovery.current.owner);
        blockCurrentSession();
        clear();
        notify({ type: "logout" });
        return;
      }
      accountRef.current = null;
      setAccount(null);
      if (recovery.current.owner) {
        setStatus("expired");
        setBrief({ ...emptyBrief });
        setAction(null);
        setDraft(null);
        setTitle("");
      } else {
        setStatus("guest");
        setBrief({ ...recovery.current.brief });
        setAction(recovery.current.actionId);
        setTitle(recovery.current.draftTitle || "");
      }
    } catch {
      // An ambiguous network failure hides account data, retaining recovery for a later check.
      if (version === epoch.current) {
        invalidatePhotos({ privateOnly: true });
        accountRef.current = null;
        setAccount(null);
        setBrief(
          recovery.current.owner
            ? { ...emptyBrief }
            : { ...recovery.current.brief },
        );
        setAction(recovery.current.owner ? null : recovery.current.actionId);
        setDraft(null);
        setTitle(recovery.current.owner ? "" : recovery.current.draftTitle || "");
        setStatus(recovery.current.owner ? "expired" : "guest");
      }
    }
  }, [adopt, clear]);

  useEffect(() => {
    persist();
    void refresh();
    const focus = () => {
      void refresh();
    };
    const storage = (event: StorageEvent) => {
      const owner = accountRef.current?.id || recovery.current.owner;
      if (owner && event.key === activeKey && activeLogin()?.id === owner) {
        invalidatePhotos({ owner });
        epoch.current++;
        accountRef.current = null;
        setAccount(null);
        setStatus('loading');
        void refresh();
        return;
      }
      if (owner && (event.key === null || event.key === invalidationPrefix + owner || event.key === activeKey)) {
        epoch.current++;
        clear();
      }
      if (event.key !== noticeKey || !event.newValue) return;
      try {
        const notice = JSON.parse(event.newValue);
        if (
          notice.type === "logout" ||
          (notice.id &&
            recovery.current.owner &&
            notice.id !== recovery.current.owner)
        ) {
          epoch.current++;
          if (notice.type === "logout") blockCurrentSession();
          clear();
        }
        if (notice.type === "account") {
          try {
            sessionStorage.removeItem(logoutKey);
          } catch {
            /* Refresh remains fenced in memory. */
          }
          void refresh();
        }
      } catch {
        /* Ignore malformed unrelated storage notifications. */
      }
    };
    window.addEventListener("focus", focus);
    window.addEventListener("storage", storage);
    const timer = window.setInterval(focus, 30000);
    return () => {
      window.removeEventListener("focus", focus);
      window.removeEventListener("storage", storage);
      window.clearInterval(timer);
    };
  }, [refresh, clear, persist]);

  async function authenticate(
    mode: "login" | "register",
    data: Record<string, string>,
  ) {
    if (loggingOut.current)
      throw new Error("Wait for logout to finish before logging in.");
    const guestAtStart = status === 'expired' ? guest.snapshot : null;
    const privateAtStart = { ...recovery.current };
    const response = await fetch(`/api/auth/${mode}`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const body = await response.json();
    if (!response.ok)
      throw new Error(
        body.detail?.code === "email_unavailable"
          ? "This email is unavailable. Try logging in."
          : "We could not sign you in. Check your details and try again.",
      );
    epoch.current++;
    const publicBrief = guestAtStart?.();
    if (publicBrief?.edited) {
      if (privateAtStart.owner === body.id) rememberPrevious(privateAtStart);
      else rememberPrevious(null);
      recovery.current = { owner: body.id, generation: generation(body.id),
        brief: publicBrief.brief, origin: publicBrief.origin, started: true,
        defaultsAttempted: true, actionId: null, draftRef: null, draftTitle: publicBrief.draftTitle };
      clearGuest();
    }
    beginLogin(body);
    adopt(body);
    notify({ type: "account", id: body.id });
  }

  async function logout() {
    if (loggingOut.current) return;
    const csrf = accountRef.current?.csrf_token;
    const owner = accountRef.current?.id || recovery.current.owner;
    loggingOut.current = true;
    epoch.current++;
    invalidate(owner);
    blockCurrentSession();
    clear();
    notify({ type: "logout" });
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "same-origin",
        headers: { "X-CSRF-Token": csrf || "" },
      });
      if (!response.ok && response.status !== 401)
        throw new Error("Logout failed");
    } catch {
      throw new Error(
        "Could not end the server session. Please log in again before continuing.",
      );
    } finally {
      epoch.current++;
      blockCurrentSession();
      invalidate(owner);
      clear();
      loggingOut.current = false;
      notify({ type: "logout" });
    }
  }

  async function deleteAccount(password: string) {
    const owner = accountRef.current;
    if (!owner || loggingOut.current) throw new Error("Log in again before deleting your account.");
    const stillCurrent = () => accountRef.current?.id === owner.id && accountRef.current?.csrf_token === owner.csrf_token;
    let response: Response;
    try {
      response = await fetch("/api/auth/account", {
        method: "DELETE", credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": owner.csrf_token },
        body: JSON.stringify({ password, confirmed: true }),
      });
    } catch {
      if (stillCurrent()) await refresh();
      throw new Error("Could not confirm account deletion. Check your connection and try again.");
    }
    if (response.status !== 204) {
      const body = await response.json().catch(() => null);
      if (response.status === 401 && stillCurrent()) await refresh();
      const messages: Record<string, string> = {
        protected_test_account: "The default test account cannot be deleted.",
        invalid_password: "Your current password is incorrect.",
        account_tasks_active: "Stop active planning tasks before deleting your account.",
      };
      throw new Error(messages[body?.detail?.code] || "Your account could not be deleted. Check your session and try again.");
    }
    invalidate(owner.id);
    if (stillCurrent()) {
      epoch.current++;
      blockCurrentSession();
      clear();
    }
  }

  function editBrief(next: Brief) {
    if (status === "loading" || status === "expired") return;
    recovery.current.brief = next;
    recovery.current.origin = "edited";
    briefRevision.current++;
    setBriefOrigin("edited");
    setBrief(next);
    persist();
  }
  const initializeNewBrief = useCallback(async () => {
    const owner = accountRef.current?.id;
    if (recovery.current.origin !== "new" || recovery.current.defaultsAttempted || recovery.current.draftRef) return;
    recovery.current.started = true;
    persist();
    if (!owner) return;
    recovery.current.defaultsAttempted = true;
    const revision = briefRevision.current;
    persist();
    try {
      const response = await fetch("/api/profile", { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) {
        if (response.status === 401) await refresh();
        return;
      }
      const profile = await response.json();
      if (accountRef.current?.id !== owner || revision !== briefRevision.current || recovery.current.origin !== "new" || loggingOut.current || sessionBlocked()) return;
      const next = briefFromProfile(profile);
      recovery.current.brief = next;
      setBrief(next);
      setDefaultsApplied(true);
      persist();
    } catch { /* Defaults are optional; the visible empty editor remains usable. */ }
  }, [persist, refresh]);
  function newBrief() {
    if (status === "loading" || status === "expired") return;
    briefRevision.current++;
    recovery.current = { owner: accountRef.current?.id || null, brief: createBrief(), actionId: null, origin: "new", started: true, generation: accountRef.current ? generation(accountRef.current.id) : undefined };
    setBrief(recovery.current.brief);
    setAction(null);
    setBriefOrigin("new");
    setDefaultsApplied(false);
    setDraft(null);
    setTitle("");
    persist();
    void initializeNewBrief();
  }
  function setDraftTitle(next: string) {
    if (status === "loading" || status === "expired") return;
    recovery.current.draftTitle = next;
    setTitle(next);
    persist();
  }
  function setDraftRef(next: DraftRef | null) {
    if (status === "loading" || status === "expired") return;
    recovery.current.draftRef = next;
    if (next) {
      briefRevision.current++;
      recovery.current.origin = "draft";
      recovery.current.defaultsAttempted = true;
      setBriefOrigin("draft");
    }
    setDraft(next);
    persist();
  }
  function replaceBrief(next: Brief, origin: "draft" | "replan" | "restored") {
    if (status === "loading" || status === "expired") return;
    briefRevision.current++;
    recovery.current.brief = restoreBrief(next);
    recovery.current.origin = origin;
    recovery.current.defaultsAttempted = true;
    recovery.current.actionId = null;
    if (origin !== "draft") {
      recovery.current.draftRef = null;
      recovery.current.draftTitle = "";
      setDraft(null);
      setTitle("");
    }
    setBrief(recovery.current.brief);
    setBriefOrigin(origin);
    setDefaultsApplied(false);
    setAction(null);
    persist();
  }
  function setActionId(next: string | null) {
    if (status === "loading" || status === "expired") return;
    recovery.current.actionId = next;
    setAction(next);
    persist();
  }
  const hasPreviousBrief = Boolean(account && previousAvailable && previousRecovery.current?.owner === account.id &&
    (previousRecovery.current.generation || '') === generation(account.id));
  function restorePreviousBrief() {
    const current = accountRef.current;
    const saved = previousRecovery.current;
    if (!current || !saved || saved.owner !== current.id || (saved.generation || '') !== generation(current.id)) return;
    recovery.current = saved;
    rememberPrevious(null);
    adopt(current);
  }
  return (
    <SessionContext.Provider
      value={{
        account,
        status,
        brief,
        briefOrigin,
        defaultsApplied,
        initializeNewBrief,
        newBrief,
        replaceBrief,
        draftRef,
        draftTitle,
        setDraftTitle,
        setDraftRef,
        actionId,
        editBrief,
        setActionId,
        authenticate,
        logout,
        deleteAccount,
        refresh,
        hasPreviousBrief,
        restorePreviousBrief,
        ...(status === 'expired' ? guest.editor : {}),
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}

export function useSession() {
  const context = useContext(SessionContext);
  if (!context) throw new Error("Product session provider is required");
  return context;
}
