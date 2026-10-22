import type { ProductDetail } from './types';

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
  const lines = [detail.title, detail.destination,
    detail.trust === 'unverified_import' ? 'Imported content · unverified' : detail.trust === 'source_fixture' ? 'Historical example · source claims' : 'Generated itinerary · evidence snapshot',
    `Original request: ${detail.request ? JSON.stringify(detail.request) : 'unknown'}`,
    'Missing weather, costs and access facts remain unknown. Confirm before travel.',
  ];
  for (const day of detail.days) {
    lines.push('', day.date, `Weather: ${day.weather ? JSON.stringify(day.weather) : 'unknown'}`);
    if (!day.activities.length) lines.push('No scheduled activities');
    for (const activity of day.activities) {
      lines.push(`${activity.time_use === 'free_window' ? 'Free window' : 'Scheduled'}: ${activity.title} · ${activity.start_time} — ${activity.end_time}`, `Cost: ${activity.estimated_cost ? `${activity.estimated_cost.amount} ${activity.estimated_cost.currency}` : 'unknown'}`);
      for (const value of [activity.place_name, activity.location, activity.notes, activity.introduction]) if (value) lines.push(value);
    }
  }
  lines.push('', 'Connections');
  for (const transfer of detail.transfers) lines.push(`${transfer.from_activity_id} → ${transfer.to_activity_id}: ${JSON.stringify(transfer)}`);
  lines.push('', 'Optional Nearby · not scheduled');
  for (const nearby of detail.nearby) lines.push(JSON.stringify(nearby));
  if (detail.completion) lines.push('', `Review (${detail.trust === 'unverified_import' ? 'unverified source claims' : 'snapshot'}): ${JSON.stringify(detail.completion)}`);
  return lines.join('\n');
}
