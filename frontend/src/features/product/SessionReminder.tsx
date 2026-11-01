import { Link } from 'react-router-dom';

export function SessionReminder({ returnTo }: { returnTo: string }) {
  return <p className="subtle-help" role="status">Your session has expired. <Link to={`/login?return=${encodeURIComponent(returnTo)}`}>Log in again</Link> to access your private trips and briefs. You can still explore examples and plan as a guest.</p>;
}
