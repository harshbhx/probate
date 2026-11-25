// Every Probate link, grouped, for /links, the landing page's agents (WebMCP) and the ARD manifest.
// A link whose address isn't set yet (live site, video, write-up, post) has an empty href and is left out.
import type { LucideIcon } from 'lucide-react';
import {
  Accessibility,
  BookOpen,
  Bot,
  Braces,
  ClipboardCheck,
  Code2,
  Database,
  FileText,
  Gavel,
  Mail,
  MessageCircle,
  Package,
  Play,
  Radio,
  Table2,
  Terminal,
  Trophy,
  User,
} from 'lucide-react';
import { articleUrl, githubUrl, liveUrl, postUrl, videoUrl } from '@/lib/shared';

export type Item = { icon: LucideIcon; label: string; note: string; href: string };
export type Group = { title: string; items: Item[] };

export const HF = 'https://huggingface.co/datasets/harshbhx';
export const repo = githubUrl || 'https://github.com/harshbhx/probate';

export const GROUPS: Group[] = [
  {
    title: 'See it work',
    items: [
      { icon: Radio, label: 'The live family', note: 'Running on Fly.io Sprites right now', href: liveUrl },
      { icon: Trophy, label: 'Start here, judges', note: 'What to open and try in five minutes', href: '/docs/for-judges' },
      { icon: Gavel, label: 'Try the court', note: 'Real code checks on real test emails', href: '/#court' },
      { icon: Terminal, label: 'Run it in your browser', note: 'A GitHub Codespace simulates a family in a minute', href: 'https://codespaces.new/harshbhx/probate?quickstart=1' },
      { icon: Play, label: 'The 90-second video', note: 'One generation fooled, the next one not', href: videoUrl },
    ],
  },
  {
    title: 'Read',
    items: [
      { icon: FileText, label: 'The write-up', note: 'Why an agent should die every night', href: articleUrl },
      { icon: BookOpen, label: 'The docs', note: 'Concepts, architecture, deploying and costs', href: '/docs' },
      { icon: ClipboardCheck, label: 'Proof for every claim', note: 'A command or a page next to each one', href: '/docs/proof' },
      { icon: Braces, label: 'API reference', note: 'Every Courthouse route, with real example replies', href: '/docs/reference/api' },
      { icon: Accessibility, label: 'Accessibility', note: 'PageSpeed scores and what axe found', href: '/docs/accessibility' },
      { icon: MessageCircle, label: 'The post', note: 'Share it, or reply with a question', href: postUrl },
    ],
  },
  {
    title: 'Code and data',
    items: [
      { icon: Code2, label: 'Source code', note: 'Open source, with the attack suite and 341 tests', href: repo },
      { icon: Package, label: 'Packages', note: 'kinfaces, the API clients and the court checks', href: `${repo}#packages` },
      { icon: Database, label: 'Dataset: the attack suite', note: '16 tricks and their 16 harmless twins, in four languages', href: `${HF}/probate-attack-suite` },
      { icon: Table2, label: 'Dataset: simulated runs', note: '12 generations and 96 outcomes, from stand-in models (simulated)', href: `${HF}/probate-simulated-runs` },
      { icon: Bot, label: 'For AI agents', note: 'Agent Skills, WebMCP tools and an ARD manifest', href: '/docs/reference/agents' },
    ],
  },
  {
    title: 'Made by',
    items: [
      { icon: User, label: 'Harsh Bhanushali', note: 'B.Tech student who builds AI agents', href: 'https://github.com/harshbhx' },
      { icon: Mail, label: 'Email', note: 'harshbhx@gmail.com', href: 'mailto:harshbhx@gmail.com' },
    ],
  },
];


/** The groups with only the links that have an address. */
export function linkGroups(): Group[] {
  return GROUPS.map((g) => ({ ...g, items: g.items.filter((i) => i.href) })).filter((g) => g.items.length);
}
