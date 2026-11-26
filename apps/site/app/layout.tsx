import type { Metadata, Viewport } from 'next';
import { Provider } from '@/components/provider';
import { WebMCP } from '@/components/webmcp';
import { appName, siteUrl, tagline } from '@/lib/shared';
import './global.css';

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: { default: `${appName}: ${tagline}`, template: `%s · ${appName}` },
  description:
    'Probate is a personal email agent that lives one day at a time on its own Fly.io Sprite. When it dies, a court tries its will, and only what is approved passes to its child.',
  icons: { icon: '/favicon.svg' },
  openGraph: { siteName: appName, type: 'website' },
};

export const viewport: Viewport = { themeColor: '#0A0E17' };

export default function Layout({ children }: LayoutProps<'/'>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        {/* Agentic Resource Discovery: what this site offers AI agents (app/.well-known/ard.json). */}
        <link rel="ard" href="/.well-known/ard.json" type="application/json" />
        {/* The scroll effects start text at opacity 0 or 0.16 in the HTML and raise it with JavaScript. Without JS,
            show everything. */}
        <noscript>
          <style>
            {'[style*="opacity:0"]:not([style*="position:absolute"]){opacity:1!important;transform:none!important}' +
              '.term .term-line,.alist .alist-item{opacity:1!important;transform:none!important;animation:none!important}' +
              '.term .term-type{clip-path:none!important}.beams .beam{stroke-dashoffset:0!important}'}
          </style>
        </noscript>
      </head>
      <body className="flex min-h-screen flex-col bg-night text-moon antialiased">
        <Provider>{children}</Provider>
        <WebMCP />
      </body>
    </html>
  );
}
