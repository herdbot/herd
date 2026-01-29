## Code

- Delete unused code (imports, variables, functions, props, files)
- No abstractions for single use
- No handling for impossible errors
- Minimal and direct solutions
- No hardcoded fallbacks; fail explicitly if config/data is missing
- Consolidate duplicate code immediately
- Replace multiple similar functions with configuration objects
- Remove trailing whitespace and excess blank lines
- Prefer direct solutions over complex patterns
- Simplify conditional logic where possible
- After making significant code changes, run @agent-code-simplifier:code-simplifier to identify and remove cruft

## Documentation

- Professional, concise, no decorative emojis
- Unicode symbols (✓, ⚠️, ❌, ○) are fine for status indicators
- Only docs integral to system
