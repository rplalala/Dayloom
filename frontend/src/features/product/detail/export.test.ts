import { describe, expect, it } from 'vitest';
import { exportArtifact, summaryText } from './export';
import type { ProductDetail } from './types';

const detail: ProductDetail = { schema_version: 'product_detail_1', id: 'private-server-id', title: 'Past journey', destination: 'Sydney', provenance: 'imported', trust: 'unverified_import', request: null, days: [{ date: '2020-01-01', activities: [] }], nearby: [{ place_name: 'Optional', anchor_activity_id: 'missing' }], transfers: [] };
describe('faithful shared exports', () => {
  it('preserves unresolved hard visits in both JSON and text exports', () => {
    const unresolved: ProductDetail = { ...detail, completion: {
      policy_completion: 'incomplete', policy_reasons: [], preference_coverage: [], minimum_daily_coverage: [],
      required_experiences: [{ requirement: 'Visit a science centre', source_quotes: ['A science centre is required.'], target: 1, scheduled: 0, frequency: 'one_off', status: 'unverified', reason: 'matching_evidence_incomplete' }],
    } };
    expect(exportArtifact(unresolved).completion).toEqual(unresolved.completion);
    expect(summaryText(unresolved)).toContain('Visit a science centre');
    expect(summaryText(unresolved)).toContain('This experience is still missing');
    expect(summaryText(unresolved)).not.toMatch(/matching visits scheduled|At least/);
  });
  it('exports one versioned reusable wrapper without server authority', () => {
    const exported = exportArtifact(detail);
    expect(exported.schema_version).toBe('dayloom_export_1');
    expect(JSON.stringify(exported)).not.toContain('private-server-id');
    expect(exported.itinerary.days).toEqual(detail.days);
    expect(exported.request).toBeNull();
    expect(exported.origin).toEqual({ provenance: 'imported', trust: 'unverified_import', assertion: 'source_snapshot_only' });
  });
  it('distinguishes unknown facts, empty days, optional references and provenance', () => {
    const summary = summaryText(detail);
    expect(summary).toContain('Imported itinerary · details to confirm');
    expect(summary).toContain('No scheduled activities');
    expect(summary).toContain('Optional Nearby · not scheduled');
    expect(summary).toContain('Original request: unknown');
  });
  it('distinguishes each source snapshot without exporting authority', () => {
    for (const source of [
      { provenance: 'example', trust: 'source_fixture' },
      { provenance: 'generated', trust: 'generated_projection' },
      { provenance: 'imported', trust: 'unverified_import' },
    ] as const) {
      expect(exportArtifact({ ...detail, ...source }).origin).toEqual({ ...source, assertion: 'source_snapshot_only' });
    }
  });
});
