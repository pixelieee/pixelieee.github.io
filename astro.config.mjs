import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import expressiveCode from 'astro-expressive-code';

export default defineConfig({
  site: 'https://pixelieee.github.io',
  integrations: [
    expressiveCode({
      themes: ['github-dark-default', 'github-light-default'],
      themeCssSelector: (theme) => (theme.type === 'dark' ? ':root[data-theme="dark"]' : ':root[data-theme="light"]'),
      useDarkModeMediaQuery: false,
      styleOverrides: { borderRadius: '10px', codeFontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace" },
    }),
    mdx(),
    sitemap(),
  ],
});
