import { describe, expect, it } from 'vitest';

import { renderMarkdown } from '../lib/utils/markdown';

describe('renderMarkdown', () => {
  it('renders timestamp tokens as buttons', () => {
    const html = renderMarkdown('Jump at ==1:23==');
    expect(html).toContain('data-timestamp="1:23"');
    expect(html).toContain('1:23');
  });

  it('renders headings and lists', () => {
    const html = renderMarkdown('# Title\n- item one');
    expect(html).toContain('<h1>Title</h1>');
    expect(html).toContain('<ul>');
    expect(html).toContain('<li>item one</li>');
  });
});
