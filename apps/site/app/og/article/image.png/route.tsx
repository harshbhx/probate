import { generateOGImage } from 'fumadocs-ui/og';
import { theArticle } from '@/lib/article';
import { appName } from '@/lib/shared';

export const revalidate = false;

export function GET() {
  const page = theArticle();
  return generateOGImage({ title: page.data.title, description: page.data.description, site: `${appName} · the write-up` });
}
