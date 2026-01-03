import { formatTimestamp, parseTimestamp } from './timestamps';

export type Segment = {
  start: number;
  end: number;
  startLabel: string;
  endLabel: string;
  contextBefore: string;
  contextAfter: string;
  lineIndex: number;
};

const SEGMENT_REGEX = /\|:\s*([^|]+?)\s*-\s*([^|]+?)\s*:\|/g;

function normalizeToken(value: string): string {
  return value.trim().replace(/^:+|:+$/g, '');
}

function takeWords(value: string, count: number, fromEnd: boolean): string {
  const words = value.trim().split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return '';
  }
  return fromEnd ? words.slice(-count).join(' ') : words.slice(0, count).join(' ');
}

export function parseSegments(body: string): Segment[] {
  const segments: Segment[] = [];
  const lines = body.split('\n');

  lines.forEach((line, lineIndex) => {
    let match: RegExpExecArray | null = null;
    const regex = new RegExp(SEGMENT_REGEX);
    while ((match = regex.exec(line))) {
      const startRaw = normalizeToken(match[1]);
      const endRaw = normalizeToken(match[2]);
      const startSeconds = parseTimestamp(startRaw);
      const endSeconds = parseTimestamp(endRaw);
      if (startSeconds === null || endSeconds === null) {
        continue;
      }

      const startLabel = formatTimestamp(startSeconds);
      const endLabel = formatTimestamp(endSeconds);
      const before = line.slice(0, match.index).trim();
      const after = line.slice(match.index + match[0].length).trim();

      segments.push({
        start: startSeconds,
        end: endSeconds,
        startLabel,
        endLabel,
        contextBefore: takeWords(before, 4, true),
        contextAfter: takeWords(after, 4, false),
        lineIndex,
      });
    }
  });

  return segments;
}
