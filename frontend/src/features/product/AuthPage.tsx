import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useSession } from "./session";
import { CuratedPhoto } from './detail/MediaPhoto';

export function AuthPage() {
  const session = useSession();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const [params] = useSearchParams();
  return (
    <div className="auth-scene">
      <div className="auth-ambient">
        <span>
          EXPLORE MORE,
          <br />
          WORRY LESS.
        </span>
        <div className="auth-scene-img">
          <CuratedPhoto image="sydney" label="Sydney Harbour" fallback="/dayloom/sydney.svg" />
        </div>
      </div>
      <div className="auth-card">
        <div className="auth-mark">✧ DAYLOOM</div>
        <div className="auth-tabs" role="tablist" aria-label="Account access">
          {(["login", "register"] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              id={`auth-${tab}-tab`}
              aria-controls="auth-panel"
              tabIndex={mode === tab ? 0 : -1}
              aria-selected={mode === tab}
              className={mode === tab ? "active" : ""}
              onClick={() => {
                setMode(tab);
                setError("");
              }}
              onKeyDown={(event) => {
                if (
                  !["ArrowLeft", "ArrowRight", "Home", "End"].includes(
                    event.key,
                  )
                )
                  return;
                event.preventDefault();
                const next =
                  event.key === "Home"
                    ? "login"
                    : event.key === "End"
                      ? "register"
                      : mode === "login"
                        ? "register"
                        : "login";
                setMode(next);
                setError("");
                document.getElementById(`auth-${next}-tab`)?.focus();
              }}
            >
              {tab === "login" ? "Log in" : "Sign up"}
            </button>
          ))}
        </div>
        <section
          className="auth-pane"
          role="tabpanel"
          id="auth-panel"
          aria-labelledby={`auth-${mode}-tab`}
        >
          <h1>
            {mode === "login"
              ? "Welcome back."
              : "Your next chapter starts here."}
          </h1>
          <p className="auth-intro">
            {mode === "login"
              ? "Pick up where your travel ideas left off."
              : "Create an account for the journeys ahead."}
          </p>
          <form
            onSubmit={async (event) => {
              event.preventDefault();
              const fields = new FormData(event.currentTarget);
              if (
                mode === "register" &&
                fields.get("password") !== fields.get("confirm")
              ) {
                setError("Your passwords do not match.");
                return;
              }
              setBusy(true);
              setError("");
              try {
                const data: Record<string, string> = {
                  email: String(fields.get("email")),
                  password: String(fields.get("password")),
                };
                if (mode === "register")
                  data.display_name = String(fields.get("display_name"));
                await session.authenticate(mode, data);
                const target = params.get("return");
                const draftReturn = target && /^\/plan\?draft=[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(target);
                const itemReturn = target && /^\/(?:trips|previews|planning)\/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(target);
                const exampleReturn = target && ['/examples/sydney-example', '/examples/kyoto-design', '/examples/melbourne-design', '/examples/nearby-linking'].includes(target);
                navigate(
                  target && (["/plan", "/trips", "/import", "/copy-recovery", "/account", "/planning"].includes(target) || draftReturn || itemReturn || exampleReturn)
                    ? target
                    : "/trips",
                  { replace: true },
                );
              } catch (failure) {
                setError(
                  failure instanceof Error
                    ? failure.message
                    : "Unable to sign in. Try again.",
                );
              } finally {
                setBusy(false);
              }
            }}
          >
            {mode === "register" && (
              <label className="field">
                <span>Display name</span>
                <input
                  name="display_name"
                  required
                  maxLength={80}
                  autoComplete="name"
                />
              </label>
            )}
            <label className="field">
              <span>Email address</span>
              <input
                name="email"
                type="email"
                required
                maxLength={254}
                autoComplete="email"
                placeholder="you@example.com"
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                name="password"
                type="password"
                required
                minLength={10}
                maxLength={128}
                autoComplete={
                  mode === "register" ? "new-password" : "current-password"
                }
                placeholder="At least 10 characters"
              />
            </label>
            {mode === "register" && (
              <label className="field">
                <span>Confirm password</span>
                <input
                  name="confirm"
                  type="password"
                  required
                  minLength={10}
                  maxLength={128}
                  autoComplete="new-password"
                />
              </label>
            )}
            {error && (
              <p role="alert" className="form-error">
                {error}
              </p>
            )}
            <button
              className="btn btn-primary btn-large btn-full"
              disabled={busy}
              type="submit"
            >
              {busy
                ? "Please wait…"
                : mode === "login"
                  ? "Log in"
                  : "Create account"}
            </button>
          </form>
        </section>
        <div className="auth-privacy">
          Your plans and preferences, together in one place.
        </div>
      </div>
    </div>
  );
}
