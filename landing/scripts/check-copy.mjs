/**
 * Fails the build if banned punctuation reaches the landing page.
 *
 * The em dash is the actual rule. The other three are here because they are
 * exactly what gets substituted when someone is told to stop using em dashes,
 * so banning only U+2014 just moves the problem one character sideways.
 *
 * Runs on every build (see package.json) because this is a rule that gets
 * broken by future edits, not by the first draft.
 */
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const ROOT = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const DIRS = ["app", "components", "lib"];
const EXTENSIONS = [".ts", ".tsx", ".css", ".mjs"];

const BANNED = [
  [/—/, "em dash (U+2014). Use a comma, a full stop, or brackets."],
  [/–/, "en dash (U+2013). Same rule as the em dash."],
  [/(?<=\s)--(?=\s)/, "double hyphen standing in for a dash."],
  [/…/, "ellipsis character (U+2026). Write three dots or restructure."],
];

function* walk(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    if (statSync(path).isDirectory()) yield* walk(path);
    else if (EXTENSIONS.some((e) => entry.endsWith(e))) yield path;
  }
}

let failures = 0;
for (const dir of DIRS) {
  const full = join(ROOT, dir);
  try {
    statSync(full);
  } catch {
    continue; // directory not created yet
  }
  for (const file of walk(full)) {
    const lines = readFileSync(file, "utf8").split("\n");
    lines.forEach((line, i) => {
      for (const [pattern, reason] of BANNED) {
        const match = pattern.exec(line);
        if (!match) continue;
        failures += 1;
        console.error(
          `${relative(ROOT, file)}:${i + 1}:${match.index + 1}  ${reason}\n    ${line.trim()}`,
        );
      }
    });
  }
}

if (failures > 0) {
  console.error(`\n${failures} banned character(s) found in landing page copy.`);
  process.exit(1);
}
console.log("copy check passed: no em dashes");
