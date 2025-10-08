# Music Shelf Audit

**Type:** - Node.js + TypeScript CLI tool

**Duration:** - Two weeks (Day 3 → Day 12)

**Goal:** - Analyze a music folder’s metadata, detect duplicates and anomalies, and generate a detailed report of the collection’s completeness and structure.

---

## Overview

Music Shelf Audit is a lightweight command-line utility that scans a local music library and produces two key outputs:

1. `report.md` - A human-readable summary including totals, durations, top artists and composers, missing tags, duplicates, and anomalies.
2. `issues.csv` - A structured log containing one entry per problem file (missing tag, duplicate, or anomaly).

The program performs a full read-only audit without renaming or modifying any files.

---

## Purpose

The goal of this project is to create a simple, self-contained tool that gives users a clear picture of the state of their music collection.
It serves as a “library health check,” identifying which tags are missing, how consistent metadata is across files, and whether there are duplicate or abnormal entries.
This makes it ideal for users who maintain large local libraries and want to improve metadata consistency before editing or reorganizing files with other tools.

---

## Features

- Scans all supported audio files (`.mp3`, `.flac`, `.m4a`, `.wav`, `.ogg`)
- Reads and records:

  - Artist, album, title, composer
  - Duration, sample rate, bit depth, codec
- Reports:

  - Missing metadata (artist, album, title, duration)
  - Duplicates (based on file size + duration + title heuristic)
  - Technical anomalies (low sample rate, extreme duration, etc.)
- Summarizes:

  - Total files, total duration, average track length
  - Top 10 artists and composers
  - Missing-tag counts
- Outputs:

  - Markdown summary (`report.md`)
  - CSV issue log (`issues.csv`)

---

## Tech Stack

- Node.js 20+
- TypeScript 5
- music-metadata (metadata extraction)
- fast-glob (directory scanning)
- csv-writer (CSV output)
- tsx (TypeScript runner)
- Optional: SQLite (for cached audits, stretch goal)

---

## File Structure

*(Subject to change as development continues)*

```
music-shelf-audit/
  README.md
  package.json
  tsconfig.json
  /src
    /cli/
      index.ts
    /core/
      scan.ts
      model.ts
      hash.ts
    /report/
      renderMarkdown.ts
      writeCsv.ts
    /persistence/
      sqlite.ts
  /test/
    scan.test.ts
```

---

## Naming and Conventions

| Category      | Convention                                            | Example                                      |
| ------------- | ----------------------------------------------------- | -------------------------------------------- |
| Branches      | feature/<slug>, fix/<slug>, chore/<slug>, docs/<slug> | feature/scanner                              |
| Commits       | Conventional commit prefixes                          | feat: add tag reader                         |
| Files/Folders | kebab-case                                            | /src/core/hash.ts                            |
| Variables     | camelCase                                             | totalDuration                                |
| Types/Classes | PascalCase                                            | TrackRecord                                  |
| CLI Name      | `msa`                                                 | `npx tsx src/cli/index.ts --path "E:\Music"` |

---

## Acceptance Criteria (v0.1.0)

- CLI scans a directory and completes successfully on a medium library (<30,000 files).
- report.md includes:

  - Totals and total duration
  - Average track length
  - Top artists and composers
  - Missing-tag counts
  - Duplicate summary
  - Anomalies section
- issues.csv lists all files with missing tags, duplicates, or anomalies.
- The tool handles errors gracefully and skips unreadable files.
- The tool performs strictly read-only operations.

---

## Day-by-Day Plan

### Week 1

**Day 3 (Today)**

- Initialize TypeScript project (`tsx`, `eslint`, `prettier`)
- Add directory scanner using `fast-glob`
- Print list of detected files
- Branch: `feature/scanner`

**Day 4**

- Integrate `music-metadata` for reading basic tags (artist, album, title, composer, duration, sample rate, bit depth)
- Print sample metadata for first few tracks
- Branch: `feature/tag-reader`

**Day 5**

- Compute totals and averages
- Display top artists and composers
- Branch: `feature/aggregates`

**Day 6**

- Implement duplicate heuristic (file size + duration + normalized title)
- Track missing tags per category
- Branch: `feature/duplicates`

### Week 2

**Day 7 (Monday)**

- Generate `report.md` with summary sections
- Branch: `feature/report-markdown`

**Day 8 (Tuesday)**

- Implement `issues.csv` with problem_type and details columns
- Branch: `feature/issues-csv`

**Day 9 (Wednesday)**

- Add anomaly checks: zero duration, low sample rate, extreme length, bit-depth mismatch
- Branch: `feature/anomalies`

**Day 10 (Thursday)**

- Add CLI flags (`--path`, `--out`, `--include`, `--exclude`, `--dry-run`)
- Branch: `feature/cli-flags`

**Day 11 (Friday)**

- Large folder test; add try/catch for metadata read errors
- Branch: `fix/stability`

**Day 12 (Saturday)**

- Final documentation polish, sample report outputs, tag `v0.1.0`
- Merge PR into `main`

---

## Stretch Goals

- Config file (`audit.config.json`) for defaults
- SQLite caching for repeat runs
- “Library Health Score” (0–100) metric based on missing tags and anomalies

---

## Scope Reduction Rules

If behind schedule:

1. Remove composer stats (keep artist only).
2. Limit anomalies to two checks (zero duration, low sample rate).
3. Keep duplicate summary only (no detailed duplicate listing).
4. Prioritize stability and correctness over feature count.

---

## Risks and Mitigation

| Risk                      | Mitigation                                       |
| ------------------------- | ------------------------------------------------ |
| Large library performance | Process files in batches; avoid full memory load |
| Metadata read failures    | Use try/catch and skip invalid files             |
| Report formatting drift   | Lock template by Day 9                           |
| Optional SQLite overrun   | Defer database until after v0.1.0                |

---

## Deliverables

- `report.md` — full summary
- `issues.csv` — detailed issue log
- Updated `README.md` with documentation and sample outputs
- Optional: `/sample-output/` folder for demonstration

---

**Project Goal Summary:**
Music Shelf Audit analyzes a music library’s metadata and generates a clear, read-only report showing missing tags, duplicates, and anomalies—helping users evaluate the completeness and integrity of their collection.