# REA/Ghidra plan for two Blood Strike procedures

## Source identity

- Requested REA source: [`morluto/rea`](https://github.com/morluto/rea), checkout `C:\Users\luiz\Documents\BloodStrikeExternal\tools\rea-source`.
- Verified commit: `0281d101307c8884f64d8d31f48e6ca982e3c42a`; package version: `6.7.0`; package binary maps `rea` and `rea-agents` to `scripts/rea.mjs`.
- Workflow documents read from this exact checkout: `AGENTS.md`, `.agents/skills/reverse-engineer-anything/SKILL.md`, its `references/native-and-artifacts.md`, `docs/ghidra-provider.md`, `docs/windows-ghidra-p0.md`, `docs/installation.md`, `docs/cli.md`, `src/cli/coreBinaryCommands.ts`, `src/cli/options.ts`.
- Target identity is the pinned Steam PE from the investigation: SHA-256 `ff080393961ac709090824356621358ae4f63dbe1c62ff636d528589cd097747`. Addresses requested: `0x1408977b0` (`GetEntityPosition`) and `0x1419c0100` (association function). This note does not validate function boundaries or names at those addresses.

## Smallest REA CLI route

REA exposes one procedure selector per `decompile` command. For example, in PowerShell after the user-installed REA CLI and Ghidra prerequisites are configured:

```powershell
$env:REA_ANALYSIS_PROVIDER = 'ghidra'
rea decompile 'C:\path\to\BloodStrike.exe' 0x1408977b0 --provider ghidra --snapshot 'C:\path\to\analysis\bloodstrike.json' --json
rea decompile 'C:\path\to\BloodStrike.exe' 0x1419c0100 --provider ghidra --snapshot 'C:\path\to\analysis\bloodstrike.json' --json
```

The equivalent positional selector is defined by `registerDecompileCommand` in `src/cli/coreBinaryCommands.ts`; it calls the `procedure_pseudo_code` workflow. The provider docs say address selectors are Ghidra analysis addresses and that REA imports one target, performs default auto-analysis, then exposes the decompiler. Thus each first-time call requires the startup/import/analysis prerequisite. `REA_GHIDRA_STARTUP_TIMEOUT_MS` extends the REA startup wait (default 330,000 ms); it is not an analysis-scope or per-function limit. Ghidra's heap can be adjusted through `GHIDRA_HEADLESS_MAXMEM` on Windows as documented in `docs/installation.md`.

## Session and snapshot reuse

A live MCP session is the way to keep one imported Ghidra Program and its persistent decompiler while asking for both addresses. Bind the PE once with `open_binary` and `provider_id: "ghidra"`, then issue two `procedure_pseudo_code` calls; close when finished. The REA skill and provider guide describe one Program per session and a persistent decompiler.

The CLI starts a separate REA process per invocation (`docs/cli.md`). `--snapshot` is useful to cache a successful exact query and reuse that same result later when target bytes, operation, selector, provider, and settings match. It stores analysis Evidence, not the Ghidra database; a second distinct address is a cache miss and still needs a provider import/auto-analysis. It does not make the second distinct function cheap by preserving the first CLI process's analysis state.

## Limiting work on a very large PE

REA 6.7.0’s Ghidra route does not offer a function-count/selected-functions auto-analysis mode. Its documented route waits for default auto-analysis. `REA_GHIDRA_DISABLED_ANALYZERS` can disable named analyzers, but only omits the facts they would produce and does not turn the rest of the import into a two-function analysis. `REA_GHIDRA_SEED_FILE` supplies known function/code/label seeds before auto-analysis; seeds improve reachability and are not a bound on total analysis. `--analysisTimeoutPerFile` is a native Ghidra headless time limit, not a selected-function count, and REA does not expose it as its scope control.

For a true two-address static pass, the direct Ghidra 12.1.4 Windows headless entry point is `support\analyzeHeadless.bat`. Its versioned `AnalyzeHeadless.java` defines `-import`, `-process`, `-noanalysis`, `-postScript`, `-readOnly`, `-deleteProject`, `-analysisTimeoutPerFile`, and `-max-cpu`. The plan is one isolated import with auto-analysis disabled and one custom `-postScript` that examines only the two supplied addresses, establishes instruction/function boundaries as necessary, and requests pseudocode for those functions. A single import/script pass can handle both. This requires writing/running a small Ghidra Java script; no tested script is included here. `-analysisTimeoutPerFile` caps elapsed auto-analysis time and can leave incomplete analysis; `-max-cpu` limits CPU parallelism. Neither is a substitute for `-noanalysis` plus explicit address selection when the goal is to avoid processing ~309k functions. Record that the function’s call targets, types, and surrounding semantics may be less recovered with auto-analysis disabled.

Ghidra's `-noanalysis` flag prevents automatic analysis; it does not itself decompile a selected function or guarantee a function definition. The post-script should verify that each address maps to initialized executable memory and an existing/created function before decompiling. Preserve failures separately (unmapped address, no function/body, and decompiler failure). Use a new temporary project directory; do not pass the game binary to a runtime/debugger. Ghidra imports for static decompilation and do not execute the target.

## Windows/version boundary and primary sources

Ghidra's official [12.1.4 release](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build) is dated 2026-09-21 and publishes SHA-256 `ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db`. Its versioned [Getting Started guide](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/GhidraDocs/GettingStarted.md) supports Windows 10 build 1809+ and lists 64-bit JDK 21. It says to extract the distribution (not install through a traditional installer) and points to `support/analyzeHeadlessREADME.html` for batch mode. The versioned [headless entry-point source](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/Ghidra/Features/Base/src/main/java/ghidra/app/util/headless/AnalyzeHeadless.java) is the direct verification for CLI flags, including `-noanalysis` and `-process`; the corresponding [HeadlessAnalyzer source](https://github.com/NationalSecurityAgency/ghidra/blob/Ghidra_12.1.4_build/Ghidra/Features/Base/src/main/java/ghidra/app/util/headless/HeadlessAnalyzer.java) covers the processing lifecycle. Ghidra 12.1.4’s release tag and the REA checkout’s Windows provider guide agree on Windows x64 support; REA says its tested Ghidra version is 12.1.4 and requires the corresponding bring-your-own installation/JDK. No Ghidra or Java installation was performed or inspected in this task.

REA primary sources: [`package.json` at the pinned commit](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/package.json), [`src/cli/coreBinaryCommands.ts`](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/src/cli/coreBinaryCommands.ts), [`docs/cli.md`](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/docs/cli.md), [`docs/ghidra-provider.md`](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/docs/ghidra-provider.md), [`docs/installation.md`](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/docs/installation.md), and the source skill [`reverse-engineer-anything/SKILL.md`](https://github.com/morluto/rea/blob/0281d101307c8884f64d8d31f48e6ca982e3c42a/.agents/skills/reverse-engineer-anything/SKILL.md).

## Boundary and next step

This is a workflow plan, not decompilation evidence. No REA command, Ghidra setup, target execution, or binary modification was performed. For the two pseudocode bodies with minimal analysis, run a custom Ghidra 12.1.4 post-script in a disposable headless project using explicit address inputs and `-noanalysis`; then compare the pseudocode with the already pinned static PE evidence. For full call/type context, use the REA full-analysis route with one persistent MCP session and retain its Evidence.
