import type { ProductDetail } from './types';
import { routeDuration, routeDistance, transferFeasibility, requiredExperienceNotice } from './display';

export function exportArtifact(detail: ProductDetail) {
  return {
    schema_version: 'dayloom_export_1', title: detail.title,
    origin: { provenance: detail.provenance, trust: detail.trust, assertion: 'source_snapshot_only' },
    request: detail.request, completion: detail.completion,
    itinerary: {
      output_version: 'itinerary_3', destination: detail.destination,
      start_date: detail.start_date, end_date: detail.end_date,
      description: detail.description, days: detail.days,
      ...(detail.illustration_key && { illustration_key: detail.illustration_key }),
      ...(detail.display_tags?.length && { display_tags: detail.display_tags }),
      nearby: detail.nearby, transfers: detail.transfers,
    },
  };
}

export function summaryText(detail: ProductDetail) {
  const request = detail.request;
  const lines = [detail.title, detail.destination,
    detail.provenance === 'imported' ? 'Imported itinerary · details to confirm' : detail.provenance === 'example' ? 'Example itinerary' : 'Generated itinerary',
    request ? [request.start_date, request.end_date, request.traveler_count != null ? `${request.traveler_count} travelers` : null, request.budget ? `Budget ${request.budget.currency} ${request.budget.amount}` : null, request.additional_preferences].filter(Boolean).join(' · ') : 'Original request: unknown',
    'Confirm opening hours, prices and weather before you travel.',
  ];
  for (const row of detail.completion?.required_experiences || []) {
    lines.push('', row.source_quotes.join(' ') || row.requirement,
      `${row.scheduled} matching visits scheduled · ${row.frequency === 'exact' ? 'Exactly' : 'At least'} ${row.target} required`, requiredExperienceNotice(row));
  }
  for (const day of detail.days) {
    lines.push('', day.date);
    const weather = day.weather;
    if (weather) lines.push(['Weather', weather.summary,
      weather.temperature_min_c != null ? `Low ${weather.temperature_min_c}°C` : null,
      weather.temperature_max_c != null ? `High ${weather.temperature_max_c}°C` : null,
      weather.precipitation_probability_percent != null ? `Rain chance ${weather.precipitation_probability_percent}%` : null,
      weather.max_wind_speed_kph != null ? `Wind up to ${weather.max_wind_speed_kph} km/h` : null,
      weather.attribution, weather.source_url,
    ].filter(Boolean).join(' · '));
    if (!day.activities.length) lines.push('No scheduled activities');
    for (const activity of day.activities) {
      lines.push(`${activity.time_use === 'free_window' ? 'Free time' : 'Planned visit'}: ${activity.place_name || activity.title} · ${activity.start_time} — ${activity.end_time}`, `Cost: ${activity.estimated_cost ? `${activity.estimated_cost.currency} ${activity.estimated_cost.amount}` : 'to confirm'}`);
      for (const value of [activity.location, activity.notes, activity.introduction]) if (value) lines.push(value);
    }
  }
  const activityName = (id: string) => {
    const activity = detail.days.flatMap(day => day.activities).find(activity => activity.activity_id === id);
    return activity ? activity.place_name || activity.title : 'Planned stop';
  };
  lines.push('', 'Connections');
  for (const transfer of detail.transfers) lines.push(`${activityName(transfer.from_activity_id)} → ${activityName(transfer.to_activity_id)} · ${routeDuration(transfer.provider_duration_seconds)} · ${routeDistance(transfer.distance_meters)} · ${transferFeasibility(detail, transfer).label}`, ...(transfer.attribution ? [transfer.attribution] : []));
  lines.push('', 'Optional Nearby · not scheduled');
  for (const nearby of detail.nearby) lines.push([nearby.place_name, nearby.area, nearby.reason, nearby.uncertainty, nearby.attribution].filter(Boolean).join(' · '));
  return lines.join('\n');
}
