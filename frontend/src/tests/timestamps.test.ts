import { describe, expect, it } from 'vitest';

import { formatTimestamp, parseTimestamp } from '../lib/utils/timestamps';

describe('parseTimestamp', () => {
  it('parses seconds-only input', () => {
    expect(parseTimestamp('42')).toBe(42);
  });

  it('parses minutes and seconds', () => {
    expect(parseTimestamp('2:05')).toBe(125);
  });

  it('parses hours, minutes, seconds', () => {
    expect(parseTimestamp('1:02:03')).toBe(3723);
  });

  it('returns null for invalid input', () => {
    expect(parseTimestamp('nope')).toBeNull();
  });
});

describe('formatTimestamp', () => {
  it('formats minutes and seconds', () => {
    expect(formatTimestamp(125)).toBe('2:05');
  });

  it('formats hours when needed', () => {
    expect(formatTimestamp(3723)).toBe('1:02:03');
  });
});
