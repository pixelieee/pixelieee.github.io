import {registerHooks} from 'node:module';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
const homePaths = pathToFileURL(resolve('packages/util/home-paths/src/index.ts')).href;
registerHooks({resolve(name, ctx, next) {
  return name === '@deepseek-ai/dsh-home-paths'
    ? {url: homePaths, shortCircuit: true} : next(name, ctx);
}});
const {renderAgentInstructions} = await import('./packages/context/agent-instructions/src/render.ts');
const file = (path, content) => ({absolutePath: resolve(path), displayPath: path, content});
const globalRule = file('~/.dsh/AGENTS.md', 'G'.repeat(240));
const rootRule = file('AGENTS.md', 'R'.repeat(800));
const nestedRule = file('app/AGENTS.md', 'N'.repeat(240));

for (const [maxBytes, files] of [
  [600, [rootRule, nestedRule]],
  [600, [globalRule, rootRule, nestedRule]],
  [2000, [globalRule, rootRule, nestedRule]],
]) {
  const {text, omitted, truncated} = renderAgentInstructions(files, {maxBytes});
  console.log(Buffer.byteLength(text), omitted.map(f => f.displayPath),
    truncated.map(f => [f.displayPath, f.includedBytes]));
}
