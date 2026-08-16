import { describe, expect, it } from 'vitest';
import { jobDescriptionBody, parseJobDescription, stripHtml } from '../src/lib/jobDescription';

describe('jobDescription', () => {
  it('strips title, company, and location that already sit in the header', () => {
    const body = jobDescriptionBody(
      'Full-Stack Software Engineer | $25-$30/hr\nHirely\nIndia (Remote)\n\nAbout the job\nBuild APIs and UIs for Hirely.',
      {
        title: 'Full-Stack Software Engineer | $25-$30/hr',
        company: 'Hirely',
        location: 'India (Remote)',
      },
    );
    expect(body).toContain('Build APIs and UIs for Hirely.');
    expect(body.startsWith('Hirely')).toBe(false);
  });

  it('parses LinkedIn-style headings and bullets', () => {
    const blocks = parseJobDescription(
      'About the job\nBuild the product.\n\nResponsibilities\n• Ship React features\n• Keep contrast high\n\nRequirements\n- TypeScript\n- REST APIs',
    );
    expect(blocks[0]).toEqual({ type: 'paragraph', text: 'Build the product.' });
    expect(blocks[1]).toEqual({ type: 'heading', text: 'Responsibilities' });
    expect(blocks[2]).toEqual({
      type: 'list',
      items: ['Ship React features', 'Keep contrast high'],
    });
    expect(blocks[3]).toEqual({ type: 'heading', text: 'Requirements' });
    expect(blocks[4]).toEqual({ type: 'list', items: ['TypeScript', 'REST APIs'] });
  });

  it('turns simple HTML into readable text', () => {
    expect(stripHtml('<p>Hello</p><br/>World<li>Item</li>')).toContain('Hello');
    expect(stripHtml('<p>Hello</p><br/>World<li>Item</li>')).toContain('World');
    expect(stripHtml('<p>Hello</p><br/>World<li>Item</li>')).toContain('• Item');
  });
});
