import type { Metadata, Viewport } from 'next';
import { Provider } from '@/components/provider';
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
      <body className="flex min-h-screen flex-col bg-night text-moon antialiased">
        <Provider>{children}</Provider>
      </body>
    </html>
  );
}
