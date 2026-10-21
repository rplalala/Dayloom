import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CopyControls } from './CopyControls';
import { copyIntentEvent, ownerCopyIntents } from './copyIntents';
import { useSession } from './session';

export function CopyRecoveryLink() {
  const { account } = useSession();
  const owner = account?.id;
  const [, setVersion] = useState(0);
  useEffect(() => {
    const changed = () => setVersion(value => value + 1);
    window.addEventListener(copyIntentEvent, changed);
    return () => window.removeEventListener(copyIntentEvent, changed);
  }, []);
  // Intent writes trigger a render; identities are always read under the current owner.
  if (!owner || !ownerCopyIntents(owner).some(intent => intent.key && !intent.resolved)) return null;
  return <p className="hint-strip"><Link to="/copy-recovery">Check pending copy status</Link></p>;
}

export function CopyRecoveryPage() {
  const { account, status } = useSession();
  if (status === 'loading') return <p role="status">Checking your session…</p>;
  if (!account) return <div className="container page"><h1>Your copy actions are private.</h1><Link to="/login?return=/copy-recovery">Log in</Link></div>;
  return <CopyRecoveryEntries key={account.id} owner={account.id} />;
}

function CopyRecoveryEntries({ owner }: { owner: string }) {
  // Keep checked receipts visible until this review page is left; no source read or POST occurs here.
  const [intents] = useState(() => ownerCopyIntents(owner).filter(intent => intent.key && !intent.resolved));
  return <div className="container page"><h1>Copy status</h1><p>Check an earlier copy action, including when its source is no longer available.</p>
    {!intents.length && <p>No unconfirmed copy actions in this browser tab.</p>}
    {intents.map(intent => <section className="flow-card" key={`${intent.kind}:${intent.source}`}>
      <h2>{intent.title || (intent.kind === 'example' ? 'Example itinerary' : 'Saved itinerary')}</h2>
      <CopyControls kind={intent.kind} source={intent.source} statusOnly />
    </section>)}
    <Link to="/trips">Back to My trips</Link>
  </div>;
}
