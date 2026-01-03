import { describe, expect, it } from 'vitest';

import { parseSegments } from '../lib/utils/segments';

describe('parseSegments', () => {
  it('parses segments with context', () => {
    const input = 'Warmup |0:30 - 1:10| alternate picking fast';
    const segments = parseSegments(input);
    expect(segments).toHaveLength(1);
    expect(segments[0]).toMatchObject({
      start: 30,
      end: 70,
      startLabel: '0:30',
      endLabel: '1:10',
      contextBefore: 'Warmup',
      contextAfter: 'alternate picking fast',
    });
  });

  it('trims surrounding colons in segment tokens', () => {
    const input = 'Loop |:1:05 - 2:15:| now';
    const segments = parseSegments(input);
    expect(segments[0].start).toBe(65);
    expect(segments[0].end).toBe(135);
  });
});
