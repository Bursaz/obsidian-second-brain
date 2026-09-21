# Avenox Beyin V3 integration

This fork uses OSB as the command, research, ingestion and vault-maintenance
surface, with the complete Avenox Beyin V3.2.0 system as its memory and
continuity runtime.

## Version and provenance

- Upstream: <https://github.com/avenoxai/avenoxbeyin>
- Pinned release: `v3.2.0`
- Pinned commit: `435f69ebc7e832e45f830c6a43114e9b62b8707e`
- Imported at: `integrations/avenox-v3/`
- License: MIT, retained in the imported tree

The full release source, tests, fixtures, documentation, platform hooks,
installers and release tooling are retained. A feature is not considered ported
by documentation alone: the corresponding upstream tests must run in this fork.

## Ownership boundary

| Concern | Owner |
| --- | --- |
| Identity, Companion, Core/Soul, Journal, Threads, Last-Session | Avenox V3 |
| Session lifecycle and bounded continuity context | Avenox V3 |
| Markdown-to-SQLite synchronization and retrieval | Avenox V3 |
| Receipts, history, revisions, recovery and rollback | Avenox V3 |
| Preferences, secret filter, Jev and global bridge | Avenox V3 |
| Vault schema, AI-first notes and propagation rules | OSB |
| Research, ingestion, thinking tools and slash commands | OSB |
| Optional hybrid semantic search and Obsidian MCP | OSB |

When both SessionStart hooks are registered, OSB detects an installed Avenox
runtime and suppresses its duplicate manual payload. It still publishes the OSB
skill root, so OSB commands remain usable. Avenox is the single owner of memory
context for that vault.

The default `🔮 850-Companion/` directory and Avenox's root `CLAUDE.md` are
system surfaces. OSB health, link, freshness and search scans exclude them;
Avenox continues to read them through its own source-backed companion path.

## Install safely

Always inspect the non-mutating plan first:

```bash
python scripts/install_avenox_v3.py --vault /path/to/vault --plan
```

Then run the same command without `--plan`. The wrapper refuses any vendored
Avenox version other than the reviewed V3.2.0 pin. A production rollout must
also run `beyin.py doctor` and verify a new cold session before declaring the
vault migrated.

## Complete V3.2.0 feature ledger

The integration retains and must continue to verify all of these groups:

- Local SQLite memory, Markdown authority, source hashes and vault binding
- Turkish/English lexical retrieval, aliases, strict context and abstention
- Visibility, trust, project/status filters, supersession and stale-source gates
- Atomic synchronization, effective revisions and duplicate-ID quarantine
- Idempotent receipts, immutable history and outcome projections
- Task/note creation, guarded task updates and recovery journal
- Companion identity, Core/Soul, Kurallar, Journal, Threads and Last-Session
- Context budgets, normal/economical/manual profiles and `no_memory`
- Claude, Codex, Antigravity, Hermes and OpenCode lifecycle adapters
- Skill synchronization and collision detection
- V2 migration and legacy writer retirement
- Doctor, preferences, update notifications and health evidence
- Signed/checksummed package validation, transactional update, recover and rollback
- Secret filtering and redaction counters
- Optional Jev context/review/memory/answer/auto-context modes and policy gates
- Optional bounded global bridge for non-vault projects
- Windows/macOS/Linux launchers and path/line-ending behavior
- Frozen semantic benchmark, decision-quality evidence and release verification

The imported Avenox test suite is the executable ledger. Any future Avenox
upgrade must update the pin, review upstream changes, and pass both projects'
test suites before merge.
