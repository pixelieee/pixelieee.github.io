import { defineConfig } from 'astro/config';
import mdx from '@astrojs/mdx';
import sitemap from '@astrojs/sitemap';
import expressiveCode from 'astro-expressive-code';
import rehypeAutolinkHeadings from 'rehype-autolink-headings';
import { rehypeHeadingIds } from '@astrojs/markdown-remark';

export default defineConfig({
  site: 'https://pixelieee.github.io',
  trailingSlash: 'ignore',
  markdown: {
    rehypePlugins: [
      rehypeHeadingIds,
      [rehypeAutolinkHeadings, {
        behavior: 'prepend',
        test: ['h2', 'h3'],
        properties: { className: ['anchor'], ariaHidden: 'true', tabIndex: -1 },
        content: { type: 'text', value: '#' },
      }],
    ],
  },
  integrations: [
    expressiveCode({
      themes: ['github-dark-default', 'github-light-default'],
      themeCssSelector: (theme) => (theme.type === 'dark' ? ':root[data-theme="dark"]' : ':root[data-theme="light"]'),
      useDarkModeMediaQuery: false,
      defaultProps: { wrap: true, preserveIndent: true },
      styleOverrides: {
        borderRadius: '10px',
        borderColor: 'var(--line)',
        codeBackground: 'var(--code)',
        codeFontFamily: "'JetBrains Mono', ui-monospace, Consolas, monospace",
        codeFontSize: '13.5px',
        codeLineHeight: '1.7',
        codePaddingInline: '1.1rem',
        uiFontFamily: 'var(--sans)',
        frames: {
          shadowColor: 'transparent',
          frameBoxShadowCssValue: 'none',
          editorTabBarBackground: 'var(--card)',
          editorTabBarBorderBottomColor: 'var(--line)',
          editorActiveTabBackground: 'var(--code)',
          editorActiveTabForeground: 'var(--mute)',
          editorActiveTabBorderColor: 'var(--line)',
          editorActiveTabIndicatorTopColor: 'var(--plat)',
          editorActiveTabIndicatorBottomColor: 'transparent',
          inlineButtonForeground: 'var(--mute)',
          inlineButtonBorder: 'var(--line)',
        },
        textMarkers: {
          markBackground: 'var(--plat-soft)',
          markBorderColor: 'var(--plat)',
        },
      },
    }),
    mdx(),
    sitemap(),
  ],
});
