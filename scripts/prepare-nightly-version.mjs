import { readFile, writeFile } from "node:fs/promises"

const packageJsonPath = new URL("../package.json", import.meta.url)
const packageJson = JSON.parse(await readFile(packageJsonPath, "utf8"))

const baseVersion = String(packageJson.version).replace(/-nightly\..*$/, "")
const stamp = new Date()
  .toISOString()
  .replace(/[-:TZ.]/g, "")
  .slice(0, 14)

packageJson.version = `${baseVersion}-nightly.${stamp}`

await writeFile(
  packageJsonPath,
  `${JSON.stringify(packageJson, null, 2)}\n`,
  "utf8",
)

process.stdout.write(`${packageJson.version}\n`)
