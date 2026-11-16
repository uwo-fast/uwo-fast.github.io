// @ts-check
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import projects from './src/data/projects.json' with { type: 'json' };
import areas from './src/data/areas.json' with { type: 'json' };

// One sidebar group per research area, holding its projects. A project with
// docs/ pages gets its own collapsed group, its README first as "Overview";
// one with a README alone is a link. The pages exist only after `npm run fetch`.

/** [slug, title] for each fetched page under dir, read from its front matter. */
function fetchedPages(dir) {
	if (!existsSync(dir)) return [];
	return readdirSync(dir, { recursive: true })
		.filter((f) => String(f).endsWith('.md'))
		.map((f) => {
			const head = readFileSync(join(dir, String(f)), 'utf8').split('\n---\n')[0];
			const field = (key) => {
				const line = head.split('\n').find((l) => l.startsWith(`${key}: `));
				return line ? JSON.parse(line.slice(key.length + 2)) : undefined;
			};
			return [field('slug'), field('title')];
		})
		.filter(([slug]) => slug)
		.sort(([a], [b]) => a.localeCompare(b));
}

function projectItem(project) {
	const dir = project.repo.split('/').pop();
	const pages = fetchedPages(`src/content/docs/projects/${dir}`);
	if (!pages.some(([slug]) => slug !== `projects/${dir}`)) {
		return { label: project.name, link: `/projects/${dir}/` };
	}

	const prefix = `projects/${dir}/docs`;
	const label = (title) => title.replace(`${project.name}: `, '');
	const items = [{ label: 'Overview', link: `/projects/${dir}/` }];
	const groups = new Map();
	for (const [slug, title] of pages) {
		if (slug === `projects/${dir}`) continue; // the README, already "Overview"
		if (slug === prefix) {
			items.push({ label: label(title), link: `/${slug}/` });
			continue;
		}
		const rest = slug.startsWith(`${prefix}/`) ? slug.slice(prefix.length + 1) : slug;
		const [first, ...more] = rest.split('/');
		if (more.length === 0 && !pages.some(([s]) => s.startsWith(`${prefix}/${first}/`))) {
			items.push({ label: label(title), link: `/${slug}/` });
			continue;
		}
		// A docs/ subdirectory becomes a group, its own index page first.
		if (!groups.has(first)) {
			const group = { label: first, collapsed: true, items: [] };
			groups.set(first, group);
			items.push(group);
		}
		const group = groups.get(first);
		if (more.length === 0) {
			group.label = label(title);
			group.items.unshift({ label: 'Overview', link: `/${slug}/` });
		} else {
			group.items.push({ label: label(title), link: `/${slug}/` });
		}
	}
	return { label: project.name, collapsed: true, items };
}

const projectGroups = areas
	.map((area) => ({
		label: area.title,
		collapsed: true,
		items: projects.filter((p) => p.area === area.id).map(projectItem),
	}))
	.filter((group) => group.items.length > 0);

export default defineConfig({
	site: 'https://uwo-fast.github.io',
	// /signs/<slug>/ is printed onto QR codes; every page URL ends in a slash.
	trailingSlash: 'always',
	integrations: [
		starlight({
			title: 'FAST Research Group',
			description:
				'The Free Appropriate Sustainability Technology (FAST) Research Group at Western University: open-source hardware for science, recycling, health and food.',
			logo: {
				src: './src/assets/fast-logo-light.png',
				alt: 'FAST',
			},
			favicon: '/favicon.ico',
			customCss: ['./src/styles/theme.css'],
			components: {
				MarkdownContent: './src/components/MarkdownContent.astro',
			},
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/uwo-fast' }],
			lastUpdated: false,
			pagination: false,
			sidebar: [
				{ label: 'Home', link: '/' },
				{ label: 'About', link: '/about/' },
				{ label: 'Projects', items: [{ label: 'All projects', link: '/projects/' }, ...projectGroups] },
				{ label: 'Lab signs', link: '/signs/' },
				{ label: 'Contact', link: '/contact/' },
			],
		}),
	],
});
