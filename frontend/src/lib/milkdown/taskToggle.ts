import { Plugin } from '@milkdown/prose/state';
import { $prose } from '@milkdown/utils';

const TASK_TOGGLE_WIDTH = 28;

export const taskToggle = $prose(
  () =>
    new Plugin({
      props: {
        handleClick(view, _pos, event) {
          if (!(event.target instanceof HTMLElement)) {
            return false;
          }
          if (event.button !== 0) {
            return false;
          }

          if (
            event.target.closest('button[data-timestamp]') ||
            event.target.closest('button[data-segment-start]')
          ) {
            return false;
          }

          const taskItem = event.target.closest<HTMLLIElement>('li[data-item-type="task"]');
          if (!taskItem) {
            return false;
          }

          const rect = taskItem.getBoundingClientRect();
          const offsetX = event.clientX - rect.left;
          if (offsetX > TASK_TOGGLE_WIDTH) {
            return false;
          }

          const pos = view.posAtDOM(taskItem, 0);
          const { doc, tr } = view.state;
          const $pos = doc.resolve(pos);

          for (let depth = $pos.depth; depth > 0; depth -= 1) {
            const node = $pos.node(depth);
            if (node.type.name !== 'list_item') {
              continue;
            }
            if (node.attrs.checked == null) {
              continue;
            }

            const nodePos = $pos.before(depth);
            const nextChecked = !node.attrs.checked;
            view.dispatch(
              tr.setNodeMarkup(nodePos, node.type, { ...node.attrs, checked: nextChecked }),
            );
            return true;
          }

          return false;
        },
      },
    }),
);
