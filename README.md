# claude-code-transcripts-extended

[![Tests](https://github.com/baboonzero/claude-code-transcripts-extended/actions/workflows/test.yml/badge.svg)](https://github.com/baboonzero/claude-code-transcripts-extended/actions/workflows/test.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/baboonzero/claude-code-transcripts-extended/blob/main/LICENSE)

Convert Claude Code session files (JSON or JSONL) to clean, mobile-friendly HTML pages with pagination, dark mode support, and pattern extraction.

[Example transcript](https://static.simonwillison.net/static/2025/claude-code-microjs/index.html) produced using this tool.

Read [A new way to extract detailed transcripts from Claude Code](https://simonwillison.net/2025/Dec/25/claude-code-transcripts/) for background on the original project.

## Installation

Install this tool using `uv`:

```bash
uv tool install claude-code-transcripts-extended
```

Or run it without installing:

```bash
uvx claude-code-transcripts-extended --help
```

## Usage

This tool converts Claude Code session files into browseable multi-page HTML transcripts.

There are five commands available:

- `local` (default) - select from local Claude Code sessions stored in `~/.claude/projects`
- `web` - select from web sessions via the Claude API
- `json` - convert a specific JSON or JSONL session file
- `all` - convert all local sessions to a browsable HTML archive
- `patterns` - extract your coding patterns and preferences into a knowledge bank

The quickest way to view a recent local session:

```bash
claude-code-transcripts-extended
```

This shows an interactive picker to select a session, generates HTML, and opens it in your default browser.

### Output options

All commands support these options:

- `-o, --output DIRECTORY` - output directory (default: writes to temp dir and opens browser)
- `-a, --output-auto` - auto-name output subdirectory based on session ID or filename
- `--repo OWNER/NAME` - GitHub repo for commit links (auto-detected from git push output if not specified)
- `--open` - open the generated `index.html` in your default browser (default if no `-o` specified)
- `--gist` - upload the generated HTML files to a GitHub Gist and output a preview URL
- `--json` - include the original session file in the output directory

The generated output includes:

- `index.html` - an index page with a timeline of prompts and commits
- `page-001.html`, `page-002.html`, etc. - paginated transcript pages

### Dark mode

The generated HTML pages support both light and dark modes:

- **Automatic detection**: Pages automatically follow your system's light/dark preference via `prefers-color-scheme`
- **Manual toggle**: Click the ☾/☼ button in the top-right corner to switch themes
- **Persistent**: Your preference is saved in localStorage and remembered across page loads

### Local sessions

Local Claude Code sessions are stored as JSONL files in `~/.claude/projects`. Run with no arguments to select from recent sessions:

```bash
claude-code-transcripts-extended
# or explicitly:
claude-code-transcripts-extended local
```

Use `--limit` to control how many sessions are shown (default: 10):

```bash
claude-code-transcripts-extended local --limit 20
```

### Web sessions

Import sessions directly from the Claude API:

```bash
# Interactive session picker
claude-code-transcripts-extended web

# Import a specific session by ID
claude-code-transcripts-extended web SESSION_ID

# Import and publish to gist
claude-code-transcripts-extended web SESSION_ID --gist
```

On macOS, API credentials are automatically retrieved from your keychain (requires being logged into Claude Code). On other platforms, provide `--token` and `--org-uuid` manually.

### Publishing to GitHub Gist

Use the `--gist` option to automatically upload your transcript to a GitHub Gist and get a shareable preview URL:

```bash
claude-code-transcripts-extended --gist
claude-code-transcripts-extended web --gist
claude-code-transcripts-extended json session.json --gist
```

This will output something like:

```
Gist: https://gist.github.com/username/abc123def456
Preview: https://gistpreview.github.io/?abc123def456/index.html
Files: /var/folders/.../session-id
```

The preview URL uses [gistpreview.github.io](https://gistpreview.github.io/) to render your HTML gist. The tool automatically injects JavaScript to fix relative links when served through gistpreview.

Combine with `-o` to keep a local copy:

```bash
claude-code-transcripts-extended json session.json -o ./my-transcript --gist
```

**Requirements:** The `--gist` option requires the [GitHub CLI](https://cli.github.com/) (`gh`) to be installed and authenticated (`gh auth login`).

### Auto-naming output directories

Use `-a/--output-auto` to automatically create a subdirectory named after the session:

```bash
# Creates ./session_ABC123/ subdirectory
claude-code-transcripts-extended web SESSION_ABC123 -a

# Creates ./transcripts/session_ABC123/ subdirectory
claude-code-transcripts-extended web SESSION_ABC123 -o ./transcripts -a
```

### Including the source file

Use the `--json` option to include the original session file in the output directory:

```bash
claude-code-transcripts-extended json session.json -o ./my-transcript --json
```

This will output:

```
JSON: ./my-transcript/session_ABC.json (245.3 KB)
```

This is useful for archiving the source data alongside the HTML output.

### Converting from JSON/JSONL files

Convert a specific session file directly:

```bash
claude-code-transcripts-extended json session.json -o output-directory/
claude-code-transcripts-extended json session.jsonl --open
```

When using [Claude Code for web](https://claude.ai/code) you can export your session as a `session.json` file using the `teleport` command.

### Converting all sessions

Convert all your local Claude Code sessions to a browsable HTML archive:

```bash
claude-code-transcripts-extended all
```

This creates a directory structure with:

- A master index listing all projects
- Per-project pages listing sessions
- Individual session transcripts

Options:

- `-s, --source DIRECTORY` - source directory (default: `~/.claude/projects`)
- `-o, --output DIRECTORY` - output directory (default: `./claude-archive`)
- `--include-agents` - include agent session files (excluded by default)
- `--dry-run` - show what would be converted without creating files
- `--open` - open the generated archive in your default browser
- `-q, --quiet` - suppress all output except errors

Examples:

```bash
# Preview what would be converted
claude-code-transcripts-extended all --dry-run

# Convert all sessions and open in browser
claude-code-transcripts-extended all --open

# Convert to a specific directory
claude-code-transcripts-extended all -o ./my-archive

# Include agent sessions
claude-code-transcripts-extended all --include-agents
```

### Pattern extraction

Extract your coding patterns and preferences from your Claude Code sessions into a personal knowledge bank. This feature uses the Anthropic API to analyze your conversations and identify recurring instructions, coding style patterns, and corrections.

**Requirements:** An Anthropic API key is required. Set it via environment variable:

```bash
# Windows PowerShell (permanent)
[System.Environment]::SetEnvironmentVariable('ANTHROPIC_API_KEY', 'your-key-here', 'User')

# macOS/Linux
export ANTHROPIC_API_KEY="your-key-here"
```

Or pass it directly with `--api-key`:

```bash
claude-code-transcripts-extended patterns --api-key "your-key-here"
```

**Usage examples:**

```bash
# Run full analysis (extracts prompts + LLM analysis)
claude-code-transcripts-extended patterns

# Extract prompts only (no API calls, useful for preview)
claude-code-transcripts-extended patterns --extract-only

# Review patterns interactively before saving
claude-code-transcripts-extended patterns --review

# Analyze only new sessions since last run
claude-code-transcripts-extended patterns --update

# Specify custom output path
claude-code-transcripts-extended patterns -o ./my_knowledge_bank.md
```

The output is a Markdown file (`my_patterns.md` by default) containing your discovered patterns organized by category.

## Acknowledgements

This project is based on [claude-code-transcripts](https://github.com/simonw/claude-code-transcripts) by [Simon Willison](https://github.com/simonw), licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

## Development

To contribute to this tool, first checkout the code. You can run the tests using `uv run`:

```bash
cd claude-code-transcripts-extended
uv run pytest
```

And run your local development copy of the tool like this:

```bash
uv run claude-code-transcripts-extended --help
```
