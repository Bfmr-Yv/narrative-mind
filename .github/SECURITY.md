# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 4.0.x   | ✅ Currently in development |

## Reporting a Vulnerability

Do **not** open a public issue for security vulnerabilities.

Please report security issues directly to: **18992570731@163.com**

You will receive a response within 48 hours. Please allow time for the issue
to be addressed before public disclosure.

## Security Considerations for Narrative Mind

- **API Keys**: Never commit API keys to the repository. Use environment
  variables or `config/llm.json` (gitignored).
- **LLM Configuration**: The `config/llm.json` file contains API credentials
  and should not be shared.
- **Corpus Data**: Corpus files may contain copyrighted material. Only
  public domain or properly licensed texts should be included.
