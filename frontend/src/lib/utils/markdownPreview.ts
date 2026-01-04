import { renderCATL } from '@j6k4m8/catl-render';

const TIMESTAMP_REGEX = /==([^=]+)==/g;
const SEGMENT_REGEX = /\|:\s*([^|]+?)\s*-\s*([^|]+?)\s*:\|/g;
const BOLD_REGEX = /\*\*([^*]+)\*\*/g;
const ITALIC_REGEX = /\*([^*]+)\*/g;
const CODE_REGEX = /`([^`]+)`/g;
const HEADING_REGEX = /^(#{1,3})\s+(.*)$/;
const LIST_REGEX = /^[-*+]\s+(.*)$/;
const TASK_REGEX = /^\[( |x|X)\]\s+(.*)$/;
const CATL_FENCE_REGEX = /^```catl\s*$/i;
const FENCE_END_REGEX = /^```\s*$/;

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
    .replace(SEGMENT_REGEX, (_match, start, end) => {
      const startText = String(start).trim().replace(/^:+|:+$/g, '');
      const endText = String(end).trim().replace(/^:+|:+$/g, '');
      return `<span class="ibis-segment" data-segment-start="${startText}" data-segment-end="${endText}">${startText}–${endText}</span>`;
    })
    .replace(
      TIMESTAMP_REGEX,
      '<span class="ibis-timestamp" data-timestamp="$1">$1</span>',
    );
}

export function renderMarkdownPreview(input: string, maxLines = 3): string {
  const lines = input.split('\n');
  let html = '';
  let inList = false;
  let lineCount = 0;

  for (let i = 0; i < lines.length; i += 1) {
    if (lineCount >= maxLines) {
      break;
    }
    const rawLine = lines[i];
    const line = rawLine.trim();
    lineCount += 1;

    if (CATL_FENCE_REGEX.test(line)) {
      if (inList) {
        html += '</ul>';
        inList = false;
      }
      const blockLines: string[] = [];
      for (let j = i + 1; j < lines.length; j += 1) {
        const blockLine = lines[j];
        if (FENCE_END_REGEX.test(blockLine.trim())) {
          i = j;
          lineCount += 1;
          break;
        }
        blockLines.push(blockLine);
        lineCount += 1;
      }
      const source = blockLines.join('\n');
      let catlHtml = '';
      try {
        catlHtml = renderCATL(source);
      } catch {
        catlHtml = `<pre><code>${escapeHtml(source)}</code></pre>`;
      }
      html += `<div class="ibis-catl-block">${catlHtml}</div>`;
      continue;
    }
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
