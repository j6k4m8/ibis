import { describe, expect, it } from 'vitest';

import { renderMarkdownPreview } from '../lib/utils/markdownPreview';

describe('renderMarkdownPreview', () => {
  it('renders a limited markdown preview', () => {
    const input = '# Heading\n- [ ] Task one\n- [x] Task two\nParagraph';
    const html = renderMarkdownPreview(input, 2);
    expect(html).toContain('<h1>Heading</h1>');
    expect(html).toContain('Task one');
    expect(html).not.toContain('Task two');
    expect(html).not.toContain('Paragraph');
  });

  it('escapes HTML while keeping inline formatting', () => {
    const input = '**Bold** and <script>alert(1)</script> ==1:23== |:0:10 - 0:20:|';
    const html = renderMarkdownPreview(input, 1);
    expect(html).toContain('<strong>Bold</strong>');
    expect(html).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(html).toContain('data-timestamp="1:23"');
    expect(html).toContain('data-segment-start="0:10"');
  });

  it('renders CATL fenced blocks', () => {
    const input = '```catl\n0A:"When"\n```';
    const html = renderMarkdownPreview(input, 3);
    expect(html).toContain('ibis-catl-block');
    expect(html).toContain('<svg');
  });

});
