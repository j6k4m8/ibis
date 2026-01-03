import { InputRule } from '@milkdown/prose/inputrules';
import { $inputRule, $nodeSchema, $remark } from '@milkdown/utils';
import { visit } from 'unist-util-visit';

const TIMESTAMP_PATTERN = /==([^=]+)==/g;

function remarkTimestamp() {
  return (tree: any) => {
    visit(tree, 'text', (node: any, index: number | null, parent: any) => {
      if (!parent || typeof index !== 'number') {
        return;
      }

      const value = String(node.value ?? '');
      const parts: any[] = [];
      let lastIndex = 0;
      let match: RegExpExecArray | null = null;
      const regex = new RegExp(TIMESTAMP_PATTERN);

      while ((match = regex.exec(value))) {
        const start = match.index;
        const end = match.index + match[0].length;
        if (start > lastIndex) {
          parts.push({ type: 'text', value: value.slice(lastIndex, start) });
        }
        parts.push({ type: 'timestamp', value: match[1] });
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

const timestampSchema = $nodeSchema('timestamp', () => ({
  inline: true,
  group: 'inline',
  atom: true,
  selectable: true,
  attrs: {
    value: { default: '' },
  },
  parseDOM: [
    {
      tag: 'button[data-timestamp]',
      getAttrs: (dom: HTMLElement) => ({
        value: dom.getAttribute('data-timestamp') ?? '',
      }),
    },
  ],
  toDOM: (node: any) => [
    'button',
    {
      type: 'button',
      class: 'ibis-timestamp',
      'data-timestamp': node.attrs.value,
    },
    node.attrs.value,
  ],
  parseMarkdown: {
    match: (node: any) => node.type === 'timestamp',
    runner: (state: any, node: any, type: any) => {
      state.addNode(type, { value: node.value });
    },
  },
  toMarkdown: {
    match: (node: any) => node.type.name === 'timestamp',
    runner: (state: any, node: any) => {
      state.addNode('text', undefined, `==${node.attrs.value}==`);
    },
  },
}));

const remarkTimestampPlugin = $remark('remarkTimestamp', () => remarkTimestamp);

const timestampInputRule = $inputRule((ctx) => {
  return new InputRule(/==([^=]+)==$/, (state, match, start, end) => {
    const [, value] = match;
    return state.tr.replaceWith(start, end, timestampSchema.type(ctx).create({ value }));
  });
});

export const timestamp = [timestampSchema, remarkTimestampPlugin, timestampInputRule].flat();
