import { Icon } from '../Icon';
import { monthDay, requiredExperienceNotice } from './display';
import type { ProductDetail, RequiredExperience } from './types';

export function ExperienceGuidance({ detail, onLocate }: {
  detail: ProductDetail;
  onLocate: (date: string, activityId: string) => void;
}) {
  const trusted = detail.trust !== 'unverified_import';
  const rows = detail.completion?.required_experiences || [];
  const storedAttention = detail.completion?.attention_items || [];
  const legacyNamedGap = trusted && detail.completion?.policy_reasons.some(reason =>
    ['required_visit_obligation_unmet', 'visit_requirement_unresolved'].includes(reason));
  const extra = storedAttention.length ? storedAttention : legacyNamedGap ? [{
    title: 'A requested place',
    description: 'Your requested visits or dates are not fully arranged. Review your original request before planning again.',
    planned_visits: [],
  }] : [];
  const visitLinks = (visits?: RequiredExperience['planned_visits']) => trusted && visits?.filter(visit =>
    detail.days.some(day => day.date === visit.date && day.activities.some(activity =>
      activity.activity_id === visit.activity_id && activity.place_name === visit.place_name
    ))).map(visit => <button type="button" className="mini-link experience-link"
      key={`${visit.date}:${visit.activity_id}`} onClick={() => onLocate(visit.date, visit.activity_id)}>
      View {visit.place_name} · {monthDay(visit.date)} <Icon name="chevron" size={13} />
    </button>);
  return <>{[true, false].map(complete => {
    const items = rows.filter(row => (trusted && row.status === 'satisfied') === complete);
    if (!items.length && (complete || !extra.length)) return null;
    const heading = complete ? 'Trip highlights' : 'Still to arrange';
    return <section className="experience-section" aria-label={heading} key={heading}>
      <h3>{heading}</h3>
      <ul className="experience-list">{items.map((row, index) => <li className="experience-line" key={index}>
        <Icon name={complete ? 'check' : 'info'} size={19} />
        <div><strong>{row.requirement}</strong>
          <p>{requiredExperienceNotice(trusted ? row : { ...row, status: 'unverified' })}</p>
          {visitLinks(row.planned_visits)}
        </div>
      </li>)}{!complete && extra.map((item, index) => <li className="experience-line" key={`attention-${index}`}>
        <Icon name="info" size={19} /><div><strong>{item.title}</strong><p>{item.description}</p>
          {visitLinks(item.planned_visits)}
        </div>
      </li>)}</ul>
    </section>;
  })}</>;
}
