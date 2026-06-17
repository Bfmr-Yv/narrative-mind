# Contributing to Narrative Mind

Thank you for your interest in contributing! Narrative Mind is an AI-assisted
novel writing IDE, currently in early development.

## Development Setup

See the README for prerequisites and getting started instructions.

## How to Contribute

1. **Report bugs** — Open an issue with clear steps to reproduce
2. **Suggest features** — Open an issue with the "enhancement" label
3. **Submit code** — Fork the repo, create a feature branch, and open a PR

## Pull Request Process

1. Ensure your code compiles: `cd src-tauri && cargo check --workspace`
2. Ensure tests pass: `cd src-tauri && cargo test --workspace`
3. Follow existing code style (Rust: `snake_case`, TypeScript: `camelCase`)
4. Update documentation if applicable
5. Open a PR with a clear description of changes

## Code Guidelines

- Rust: Edition 2024, standard library + tokio + rusqlite + reqwest + serde
- Python: Type hints required, follow PEP 8
- TypeScript: Use `camelCase` for variables, `PascalCase` for components

## Questions?

Open an issue or contact the maintainer.
