import { createMDX } from 'fumadocs-mdx/next';

const withMDX = createMDX();

/** @type {import('next').NextConfig} */
const config = {
  output: 'export',
  reactStrictMode: true,
  // The stylesheet (about 27 KB compressed) goes into each page's HTML instead of a render-blocking request.
  experimental: { inlineCss: true },
  transpilePackages: ['kinfaces', '@probate/moments'],
};

export default withMDX(config);
