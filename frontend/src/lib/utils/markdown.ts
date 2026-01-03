const TIMESTAMP_REGEX = /==([^=]+)==/g;
const BOLD_REGEX = /\*\*([^*]+)\*\*/g;
const ITALIC_REGEX = /\*([^*]+)\*/g;
const CODE_REGEX = /`([^`]+)`/g;
const HEADING_REGEX = /^(#{1,3})\s+(.*)$/;
const LIST_REGEX = /^[-*]\s+(.*)$/;
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
  return text
    .replace(CODE_REGEX, '<code>$1</code>')
    .replace(BOLD_REGEX, '<strong>$1</strong>')
    .replace(ITALIC_REGEX, '<em>$1</em>')
    .replace(TIMESTAMP_REGEX, '<button class="ibis-timestamp" data-timestamp="$1">$1</button>');
}

export function renderMarkdown(input: string): string {
  const escaped = escapeHtml(input);
  const lines = escaped.split('\n');
  let html = '';
  let inList = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      html += '<div class="ibis-spacer"></div>';
      continue;
    }

    const headingMatch = line.match(HEADING_REGEX);
    if (headingMatch) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      const level = headingMatch[1].length;
      const content = renderInline(headingMatch[2]);
      html += `<h${level}>${content}</h${level}>`;
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
        const taskText = renderInline(taskMatch[2]);
        const checkboxClass = checked ? 'ibis-checkbox checked' : 'ibis-checkbox';
        content = `<span class="${checkboxClass}">${checked ? '✓' : ''}</span>${taskText}`;
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
