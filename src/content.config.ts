import { defineCollection, z } from 'astro:content';
import { glob } from 'astro/loaders';

const notes = defineCollection({
  loader: glob({ pattern: '**/*.{md,mdx}', base: './src/content/notes' }),
  schema: z.object({
    title: z.string(),
    titleEn: z.string().optional(),
    /** 一行导语，显示在标题下方。 */
    dek: z.string().optional(),
    summary: z.string(),
    summaryEn: z.string().optional(),
    date: z.string(),
    updated: z.string().optional(),
    topic: z.string().default('Agent 工程'),
    status: z.enum(['published', 'draft', 'todo']).default('draft'),
    pinned: z.string().optional(),
  }),
});

export const collections = { notes };
