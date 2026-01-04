import { renderCATL } from '@j6k4m8/catl-render';
import { Plugin } from '@milkdown/prose/state';
import { $prose } from '@milkdown/utils';

function getLanguage(node: { attrs?: Record<string, unknown> }) {
  const raw = node?.attrs?.language ?? node?.attrs?.lang ?? '';
  return String(raw).toLowerCase();
}

function renderPreview(container: HTMLElement, source: string) {
  try {
    container.innerHTML = renderCATL(source);
  } catch (error) {
    container.textContent = source;
  }
}

export const catl = $prose(
  () =>
    new Plugin({
      props: {
        nodeViews: {
          code_block(node) {
            if (getLanguage(node) !== 'catl') {
              return null;
            }

            const wrapper = document.createElement('div');
            wrapper.className = 'ibis-catl-node';

            const preview = document.createElement('div');
            preview.className = 'ibis-catl-block';

            const pre = document.createElement('pre');
            const code = document.createElement('code');
            pre.append(code);

            wrapper.append(preview, pre);

            renderPreview(preview, node.textContent);

            return {
              dom: wrapper,
              contentDOM: code,
              update(updated) {
                if (updated.type !== node.type || getLanguage(updated) !== 'catl') {
                  return false;
                }
                renderPreview(preview, updated.textContent);
                return true;
              },
            };
          },
        },
      },
    }),
);
