import { defineConfig } from 'astro/config';
import tailwind from '@astrojs/tailwind';
import mdx from '@astrojs/mdx';

export default defineConfig({
  output: 'static',
  site: 'https://beguardit.com',
  integrations: [tailwind(), mdx()],
  markdown: {
    shikiConfig: { theme: 'github-dark' },
  },
});
