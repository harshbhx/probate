// One list of destinations for the header, the mobile menu and the footer.
import { githubUrl, liveUrl } from '@/lib/shared';

export const NAV = [
  { label: 'How it works', href: '/#life' },
  { label: 'The court', href: '/#court' },
  { label: 'Instincts', href: '/#instincts' },
  { label: 'Docs', href: '/docs' },
];

export type FootLink = { label: string; href: string };

export const FOOTER: { title: string; links: FootLink[] }[] = [
  {
    title: 'Product',
    links: [
      ...(liveUrl ? [{ label: 'Live family', href: liveUrl }] : []),
      { label: 'How it works', href: '/#life' },
      { label: 'Try the court', href: '/#court' },
      { label: 'Instincts', href: '/#instincts' },
      { label: 'Evidence', href: '/#evidence' },
    ],
  },
  {
    title: 'Docs',
    links: [
      { label: 'Quickstart', href: '/docs/quickstart' },
      { label: 'The court', href: '/docs/concepts/court' },
      { label: 'Architecture', href: '/docs/architecture/overview' },
      { label: 'API reference', href: '/docs/reference/api' },
      { label: 'FAQ', href: '/docs/faq' },
    ],
  },
  {
    title: 'Project',
    links: [
      ...(githubUrl ? [{ label: 'Source on GitHub', href: githubUrl }] : []),
      { label: 'Security model', href: '/docs/security' },
      { label: 'Deploy your own', href: '/docs/guides/deploy' },
      { label: 'Fly.io Hacksgiving', href: 'https://fly.io/hacksgiving/' },
      { label: 'llms.txt', href: '/llms.txt' },
    ],
  },
];
