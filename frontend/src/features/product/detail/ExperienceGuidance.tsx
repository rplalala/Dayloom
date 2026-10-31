import { Icon } from '../Icon';
import { monthDay, requiredExperienceNotice } from './display';
import type { ProductDetail } from './types';

export function ExperienceGuidance({ detail, onLocate }: {
  detail: ProductDetail;
  onLocate: (date: string, activityId: string) => void;
}) {
  const trusted = detail.trust !== 'unverified_import';
  const rows = detail.completion?.required_experiences || [];
  return <>{[true, false].map(complete => {
    const items = rows.filter(row => (trusted && row.status === 'satisfied') === complete);
    if (!items.length) return null;
    const heading = complete ? 'Trip highlights' : 'Still to arrange';
    return <section className="experience-section" aria-label={heading} key={heading}>
      <h3>{heading}</h3>
      <ul className="experience-list">{items.map((row, index) => <li className="experience-line" key={index}>
        <Icon name={complete ? 'check' : 'info'} size={19} />
        <div><strong>{row.requirement}</strong>
          <p>{requiredExperienceNotice(trusted ? row : { ...row, status: 'unverified' })}</p>
          {trusted && row.planned_visits?.filter(visit => detail.days.some(day =>
            day.date === visit.date && day.activities.some(activity =>
              activity.activity_id === visit.activity_id && activity.place_name === visit.place_name
            ))).map(visit => <button type="button" className="mini-link experience-link"
              key={`${visit.date}:${visit.activity_id}`} onClick={() => onLocate(visit.date, visit.activity_id)}>
              View {visit.place_name} · {monthDay(visit.date)} <Icon name="chevron" size={13} />
            </button>)}
        </div>
      </li>)}</ul>
    </section>;
  })}</>;
}
