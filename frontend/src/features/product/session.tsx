import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";

export type Account = {
  id: string;
  email: string;
  display_name: string;
  initials: string;
  csrf_token: string;
};
export type Brief = {
  destination: string;
  start_date: string;
  end_date: string;
  travelers: string;
  budget: string;
  currency: string;
  preferences: string;
};
export const emptyBrief: Brief = {
  destination: "",
  start_date: "",
  end_date: "",
  travelers: "",
  budget: "",
  currency: "AUD",
  preferences: "",
};
type Recovery = { owner: string | null; brief: Brief; actionId: string | null };
const key = "dayloom.editor.v1";
const noticeKey = "dayloom.account.notice";
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
  actionId: string | null;
  editBrief: (brief: Brief) => void;
  setActionId: (id: string | null) => void;
  authenticate: (
    mode: "login" | "register",
    data: Record<string, string>,
  ) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};
const SessionContext = createContext<Session | null>(null);

function readRecovery(): Recovery {
  try {
    const saved = JSON.parse(sessionStorage.getItem(key) || "null");
    if (
      saved &&
      typeof saved === "object" &&
      saved.brief &&
      Object.keys(emptyBrief).every(
        (k) => typeof saved.brief[k] === "string",
      ) &&
      (saved.owner === null || typeof saved.owner === "string") &&
      (saved.actionId === null || typeof saved.actionId === "string")
    )
      return saved;
  } catch {
    /* An unavailable storage area must not prevent planning. */
  }
  return { owner: null, brief: { ...emptyBrief }, actionId: null };
}

export function SessionProvider({ children }: { children: ReactNode }) {
  const recovery = useRef<Recovery>(readRecovery());
  const accountRef = useRef<Account | null>(null);
  const [account, setAccount] = useState<Account | null>(null);
  const [status, setStatus] = useState<Session["status"]>("loading");
  const [brief, setBrief] = useState<Brief>({ ...emptyBrief });
  const [actionId, setAction] = useState<string | null>(null);
  const epoch = useRef(0);

  const persist = useCallback(() => {
    try {
      sessionStorage.setItem(key, JSON.stringify(recovery.current));
    } catch {
      /* Memory remains usable. */
    }
  }, []);
  const clear = useCallback(() => {
    recovery.current = {
      owner: null,
      brief: { ...emptyBrief },
      actionId: null,
    };
    accountRef.current = null;
    setAccount(null);
    setBrief({ ...emptyBrief });
    setAction(null);
    setStatus("guest");
    persist();
  }, [persist]);
  const adopt = useCallback(
    (next: Account) => {
      if (recovery.current.owner && recovery.current.owner !== next.id) {
        recovery.current = {
          owner: next.id,
          brief: { ...emptyBrief },
          actionId: null,
        };
      } else recovery.current.owner = next.id;
      accountRef.current = next;
      setAccount(next);
      setStatus("authenticated");
      setBrief({ ...recovery.current.brief });
      setAction(recovery.current.actionId);
      persist();
    },
    [persist],
  );

  const refresh = useCallback(async () => {
    const version = ++epoch.current;
    try {
      const response = await fetch("/api/auth/current", {
        credentials: "same-origin",
        cache: "no-store",
      });
      const body = await response.json();
      if (version !== epoch.current) return;
      if (response.ok) {
        adopt(body);
        return;
      }
      if (response.status !== 401) throw new Error("Session unavailable");
      if (
        [
          "session_revoked",
          "invalid_session",
          "conflicting_credentials",
        ].includes(body.detail?.code)
      ) {
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
      } else {
        setStatus("guest");
        setBrief({ ...recovery.current.brief });
        setAction(recovery.current.actionId);
      }
    } catch {
      // An ambiguous network failure hides account data, retaining recovery for a later check.
      if (version === epoch.current) {
        accountRef.current = null;
        setAccount(null);
        setBrief(recovery.current.owner ? { ...emptyBrief } : { ...recovery.current.brief });
        setAction(recovery.current.owner ? null : recovery.current.actionId);
        setStatus(recovery.current.owner ? "expired" : "guest");
      }
    }
  }, [adopt, clear]);

  useEffect(() => {
    void refresh();
    const focus = () => {
      void refresh();
    };
    const storage = (event: StorageEvent) => {
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
          clear();
        } else void refresh();
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
  }, [refresh, clear]);

  async function authenticate(
    mode: "login" | "register",
    data: Record<string, string>,
  ) {
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
    adopt(body);
    notify({ type: "account", id: body.id });
  }

  async function logout() {
    const csrf = accountRef.current?.csrf_token;
    epoch.current++;
    clear();
    notify({ type: "logout" });
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
      headers: { "X-CSRF-Token": csrf || "" },
    });
    if (!response.ok && response.status !== 401)
      throw new Error(
        "Could not end the server session. Close this browser and try again.",
      );
  }

  function editBrief(next: Brief) {
    if (status === "loading" || status === "expired") return;
    recovery.current.brief = next;
    setBrief(next);
    persist();
  }
  function setActionId(next: string | null) {
    if (status === "loading" || status === "expired") return;
    recovery.current.actionId = next;
    setAction(next);
    persist();
  }
  return (
    <SessionContext.Provider
      value={{
        account,
        status,
        brief,
        actionId,
        editBrief,
        setActionId,
        authenticate,
        logout,
        refresh,
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
