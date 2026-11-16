import { defineCollection } from 'astro:content';
import { z } from 'astro/zod';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
	docs: defineCollection({
		loader: docsLoader(),
		schema: docsSchema({
			// Lab signs and equipment records carry these in their front matter
			// (scripts/fetch-signs.sh copies them from uwo-fast/uwo-fast).
			extend: z.object({
				kind: z.enum(['sign', 'equipment']).optional(),
				status: z.string().optional(),
				version: z.string().optional(),
				review_owner: z.string().optional(),
				record_owner: z.string().optional(),
				equipment: z.string().optional(),
				last_updated: z.string().optional(),
				source: z.string().optional(),
			}),
		}),
	}),
};
