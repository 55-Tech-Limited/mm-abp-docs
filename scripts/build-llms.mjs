import fs from "node:fs";
import path from "node:path";

const ROOT = process.cwd();

const DOCS_JSON_PATH = path.join(ROOT, "docs.json");
const DOCS_DIR = ROOT;
const PUBLIC_DIR = path.join(ROOT, "public");

const OUT_INDEX = path.join(PUBLIC_DIR, "llms.txt");
const OUT_FULL = path.join(PUBLIC_DIR, "llms-full.txt");

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, "utf8"));
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function fileExists(p) {
  try {
    fs.accessSync(p);
    return true;
  } catch {
    return false;
  }
}

function pageToMdxPath(page) {
  return path.join(DOCS_DIR, `${page}.mdx`);
}

function stripFrontmatter(mdx) {
  if (!mdx.startsWith("---")) return mdx;
  const match = mdx.match(/^---\s*\n[\s\S]*?\n---\s*\n/);
  if (!match) return mdx;
  return mdx.slice(match[0].length);
}

function titleFromFrontmatter(mdx) {
  const fm = mdx.match(/^---\s*\n[\s\S]*?\n---\s*\n/);
  if (!fm) return null;
  const title = fm[0].match(/^\s*title:\s*["']?(.+?)["']?\s*$/m);
  return title ? title[1].trim() : null;
}

function collectPages(docsJson) {
  const pages = [];

  // Handle both flat tabs and language-based navigation
  const languages = docsJson?.navigation?.languages;
  const tabs = languages
    ? (languages.find((l) => l.language === "en")?.tabs ?? [])
    : (docsJson?.navigation?.tabs ?? []);

  for (const tab of tabs) {
    const groups = tab?.groups ?? [];
    for (const group of groups) {
      const groupPages = group?.pages ?? [];
      for (const p of groupPages) {
        if (typeof p === "string" && p.length > 0) pages.push(p);
      }
    }
  }

  // de-dupe preserving order
  const seen = new Set();
  const ordered = [];
  for (const p of pages) {
    if (!seen.has(p)) {
      seen.add(p);
      ordered.push(p);
    }
  }
  return ordered;
}

function findOpenApiPaths(docsJson) {
  const paths = [];
  const languages = docsJson?.navigation?.languages;
  const tabs = languages
    ? (languages.find((l) => l.language === "en")?.tabs ?? [])
    : (docsJson?.navigation?.tabs ?? []);

  for (const tab of tabs) {
    for (const group of tab?.groups ?? []) {
      if (typeof group?.openapi === "string" && group.openapi.length > 0) {
        paths.push(group.openapi);
      }
    }
  }
  return paths;
}

function main() {
  if (!fileExists(DOCS_JSON_PATH)) {
    console.error(`docs.json not found at: ${DOCS_JSON_PATH}`);
    process.exit(1);
  }

  const docsJson = readJson(DOCS_JSON_PATH);
  const pages = collectPages(docsJson);
  const openapiPaths = findOpenApiPaths(docsJson);

  ensureDir(PUBLIC_DIR);

  let llmsIndex =
    `# 55-Tech API Docs (Mintlify)\n` +
    `# Generated from docs.json navigation\n\n`;

  let llmsFull =
    `# 55-Tech API Docs — Full Bundle\n` +
    `# Generated from docs.json navigation\n` +
    `# Source: MDX files\n` +
    `# APIs: ABP (Automated Bet Placing) and MM (Market Making)\n\n`;

  const missing = [];
  let includedCount = 0;

  for (const route of pages) {
    const mdxPath = pageToMdxPath(route);

    if (!fileExists(mdxPath)) {
      missing.push({ route, mdxPath });
      continue;
    }

    const raw = fs.readFileSync(mdxPath, "utf8");
    const title = titleFromFrontmatter(raw) ?? route;

    llmsIndex += `- /${route} — ${title}\n`;

    llmsFull +=
      `\n\n---\n` +
      `## ${title}\n` +
      `Source: /${route}\n` +
      `---\n\n` +
      `${stripFrontmatter(raw).trim()}\n`;

    includedCount += 1;
  }

  for (const openapiRel of openapiPaths) {
    llmsIndex += `\n# OpenAPI\n- /${openapiRel} — OpenAPI 3.1 spec\n`;

    const openapiPath = path.join(DOCS_DIR, openapiRel);
    if (fileExists(openapiPath)) {
      const spec = fs.readFileSync(openapiPath, "utf8");
      llmsFull +=
        `\n\n---\n` +
        `## OpenAPI (REST Reference)\n` +
        `Source: /${openapiRel}\n` +
        `---\n\n` +
        "```json\n" +
        spec.trim() +
        "\n```\n";
    } else {
      llmsFull +=
        `\n\n---\n` +
        `## OpenAPI (REST Reference)\n` +
        `Source: /${openapiRel}\n` +
        `---\n\n` +
        `OpenAPI file not found at: ${openapiPath}\n`;
    }
  }

  fs.writeFileSync(OUT_INDEX, llmsIndex, "utf8");
  fs.writeFileSync(OUT_FULL, llmsFull, "utf8");

  console.log(`Wrote: ${OUT_INDEX}`);
  console.log(`Wrote: ${OUT_FULL}`);
  console.log(`Included ${includedCount} MDX pages from navigation.`);

  if (missing.length) {
    console.log(`Skipped ${missing.length} nav entries with missing MDX files:`);
    for (const m of missing.slice(0, 50)) {
      console.log(`  - ${m.route} (expected ${m.mdxPath})`);
    }
    if (missing.length > 50) console.log(`  ...and ${missing.length - 50} more`);
  }
}

main();
