import rss from '@astrojs/rss';
import { getCollection } from 'astro:content';

export async function GET(context) {
  const notes = (await getCollection('notes'))
    .filter((n) => n.data.status === 'published')
    .sort((a, b) => b.data.date.localeCompare(a.data.date));
  return rss({
    title: 'pixel notes',
    description: '对照源码写成的 Agent 工程学习笔记。',
    site: context.site,
    items: notes.map((n) => ({
      title: n.data.title,
      description: n.data.summary,
      pubDate: new Date(`${n.data.date}T00:00:00+08:00`),
      link: `/notes/${n.id}/`,
    })),
    customData: '<language>zh-cn</language>',
  });
}
