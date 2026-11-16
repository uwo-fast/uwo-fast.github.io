# uwo-fast.github.io

The website of the Free Appropriate Sustainability Technology (FAST) Research Group at
Western University: <https://uwo-fast.github.io/>.

It is built with [Astro](https://astro.build/) and
[Starlight](https://starlight.astro.build/) and deployed to GitHub Pages by
`.github/workflows/pages.yml`, on every push to `main`, daily, and on demand.

## What is on it

- **Projects.** Each repository listed in `src/data/projects.json` gets a page rendered
  from its own README and `docs/`. `scripts/fetch-projects.sh` copies each repository
  into a temporary directory, and `scripts/project-pages.py` writes its pages into
  `src/content/docs/projects/<repo>/` and the images those pages use into
  `public/projects/<repo>/`. Links to anything else in the repository go to GitHub.
- **Lab signs and equipment records.** `scripts/fetch-signs.sh` copies them from
  `lab-signs/` and `equipment/` in [uwo-fast/uwo-fast](https://github.com/uwo-fast/uwo-fast)
  into `src/content/docs/signs/` and `src/content/docs/equipment/`.
- **The home, About, Contact and 404 pages**, in `src/content/docs/`.

The fetched content is not committed; the build fetches it fresh each time.

### The sign URLs are a contract

`/signs/<slug>/` and `/equipment/<slug>/` are printed onto QR codes posted in the lab.
`scripts/required-urls.txt` lists every one, and `npm run check-urls` fails the build
if any is missing. Add a sign to that list when it is first printed, and never remove
one.

## Working on the site

Requires Node 24 (`.nvmrc`), Python 3, `jq` and `git`.

```sh
npm ci
npm run fetch        # clone the projects and signs and render them
npm run dev          # http://localhost:4321/
npm run build        # the site, in dist/
npm run check-urls   # every required URL is in dist/
python3 -m unittest discover tests
```

To render from local checkouts instead of cloning, set `PROJECTS_SRC` to the directory
holding them and `SIGNS_SRC` to a checkout of uwo-fast/uwo-fast:

```sh
PROJECTS_SRC=.. SIGNS_SRC=../uwo-fast npm run fetch
```

A local checkout is read with `git archive`, which gives Git LFS pointers rather than
the files, so an LFS image shows as broken locally. The deployed site clones, and has
them.

### Listing a project

Add an entry to `src/data/projects.json`:

```json
{
  "name": "Display Name",
  "repo": "uwo-fast/repo-name",
  "area": "equipment",
  "description": "One line for its card.",
  "image": "docs/images/photo.jpg"
}
```

`area` is one of the ids in `src/data/areas.json`. The home page, the projects page
and the sidebar group projects by area, and hide an area with no projects. `image`
is optional: a path in the repository to a picture for the project's card.

## Design

The colours are Western University's, set in `src/styles/theme.css`:

| Colour | Hex | Use |
| --- | --- | --- |
| Western Purple | `#4F2683` | header, links and accents (light theme) |
| Orchid | `#8F55E0` | accents (dark theme) |
| Deep Focus | `#201436` | text on accent backgrounds |
| Grey | `#818284` | |
| Tiger | `#F0A757` | signs awaiting review |

The FAST logo is by Joshua M. Pearce, from
[Appropedia](https://www.appropedia.org/File:Purplefast.png), under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
`src/assets/fast-logo-purple.png` is that logo resized;
`src/assets/fast-logo-light.png` is the same logo in light lavender, for the purple
header and the dark theme.
