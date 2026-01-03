import { InputRule } from '@milkdown/prose/inputrules';
import { $inputRule, $nodeSchema, $remark } from '@milkdown/utils';
import { visit } from 'unist-util-visit';

const SEGMENT_REGEX = /\|([^|]+?)\s*-\s*([^|]+?)\|/g;

function remarkSegment() {
  return (tree: any) => {
    visit(tree, 'text', (node: any, index: number | null, parent: any) => {
      if (!parent || typeof index !== 'number') {
        return;
      }

      const value = String(node.value ?? '');
      const parts: any[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null = null;
      const regex = new RegExp(SEGMENT_REGEX);

      while ((match = regex.exec(value))) {
        const start = match.index;
        const end = match.index + match[0].length;
        if (start > lastIndex) {
          parts.push({ type: 'text', value: value.slice(lastIndex, start) });
        }
        parts.push({ type: 'segment', start: match[1].trim(), end: match[2].trim() });
        lastIndex = end;
      }

      if (parts.length === 0) {
        return;
      }

      if (lastIndex < value.length) {
        parts.push({ type: 'text', value: value.slice(lastIndex) });
      }

      parent.children.splice(index, 1, ...parts);
      return index + parts.length;
    });
  };
}

const segmentSchema = $nodeSchema('segment', () => ({
  inline: true,
  group: 'inline',
  atom: true,
  selectable: true,
  attrs: {
    start: { default: '' },
    end: { default: '' },
  },
  parseDOM: [
    {
      tag: 'button[data-segment-start][data-segment-end]',
      getAttrs: (dom: HTMLElement) => ({
        start: dom.getAttribute('data-segment-start') ?? '',
        end: dom.getAttribute('data-segment-end') ?? '',
      }),
    },
  ],
  toDOM: (node: any) => [
    'button',
    {
      type: 'button',
      class: 'ibis-segment',
      'data-segment-start': node.attrs.start,
      'data-segment-end': node.attrs.end,
    },
    `${node.attrs.start}–${node.attrs.end}`,
  ],
  parseMarkdown: {
    match: (node: any) => node.type === 'segment',
    runner: (state: any, node: any, type: any) => {
      state.addNode(type, { start: node.start ?? '', end: node.end ?? '' });
    },
  },
  toMarkdown: {
    match: (node: any) => node.type.name === 'segment',
    runner: (state: any, node: any) => {
      state.addNode('text', undefined, `|${node.attrs.start} - ${node.attrs.end}|`);
    },
  },
}));

const remarkSegmentPlugin = $remark('remarkSegment', () => remarkSegment);

const segmentInputRule = $inputRule((ctx) => {
  return new InputRule(/\|([^|]+?)\s*-\s*([^|]+?)\|$/, (state, match, start, end) => {
    const [, startText, endText] = match;
    return state.tr.replaceWith(
      start,
      end,
      segmentSchema.type(ctx).create({ start: startText.trim(), end: endText.trim() }),
    );
  });
});

export const segment = [segmentSchema, remarkSegmentPlugin, segmentInputRule].flat();
