const TIMESTAMP_REGEX = /==([^=]+)==/g;
const SEGMENT_REGEX = /\|([^|]+?)\s*-\s*([^|]+?)\|/g;
const BOLD_REGEX = /\*\*([^*]+)\*\*/g;
const ITALIC_REGEX = /\*([^*]+)\*/g;
const CODE_REGEX = /`([^`]+)`/g;
const HEADING_REGEX = /^(#{1,3})\s+(.*)$/;
const LIST_REGEX = /^[-*+]\s+(.*)$/;
const TASK_REGEX = /^\[( |x|X)\]\s+(.*)$/;

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function renderInline(text: string): string {
  const escaped = escapeHtml(text);
  return escaped
    .replace(CODE_REGEX, '<code>$1</code>')
    .replace(BOLD_REGEX, '<strong>$1</strong>')
    .replace(ITALIC_REGEX, '<em>$1</em>')
    .replace(
      SEGMENT_REGEX,
      '<span class="ibis-segment" data-segment-start="$1" data-segment-end="$2">$1–$2</span>',
    )
    .replace(
      TIMESTAMP_REGEX,
      '<span class="ibis-timestamp" data-timestamp="$1">$1</span>',
    );
}

export function renderMarkdownPreview(input: string, maxLines = 3): string {
  const lines = input.split('\n').slice(0, maxLines);
  let html = '';
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      continue;
    }

    const headingMatch = line.match(HEADING_REGEX);
    if (headingMatch) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      const level = headingMatch[1].length;
      html += `<h${level}>${renderInline(headingMatch[2])}</h${level}>`;
      continue;
    }

    const listMatch = line.match(LIST_REGEX);
    if (listMatch) {
      if (!inList) {
        html += '<ul>';
        inList = true;
      }
      let content = listMatch[1];
      const taskMatch = content.match(TASK_REGEX);
      if (taskMatch) {
        const checked = taskMatch[1].toLowerCase() === 'x';
        const checkboxClass = checked ? 'ibis-checkbox checked' : 'ibis-checkbox';
        content = `<span class="${checkboxClass}">${checked ? '✓' : ''}</span>${renderInline(
          taskMatch[2],
        )}`;
      } else {
        content = renderInline(content);
      }
      html += `<li>${content}</li>`;
      continue;
    }

    if (inList) {
      html += '</ul>';
      inList = false;
    }

    html += `<p>${renderInline(line)}</p>`;
  }

  if (inList) {
    html += '</ul>';
  }

  return html;
}

export function renderMarkdown(input: string): string {
  return renderMarkdownPreview(input, Number.POSITIVE_INFINITY);
}
