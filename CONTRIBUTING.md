# Contributing to `mcp-panther`

Thank you for your interest in contributing to the `mcp-panther`! We appreciate all types of contributions, including default configurations, feature requests, and bug reports.

The purpose of this repository is to help Panther users bootstrap their new `mcp-panther` repository for v2 rule management, including custom rules, overrides, helper functions, and more.

## Testing your changes

Before submitting your pull request, make sure to:

- Redact any sensitive information or PII from example logs
- Add unit tests where relevant.
- Install dev dependencies:
  ```bash
  uv pip install -e ".[dev]"
  ```
- Tests can be run with:
  ```bash
  pytest
  ```
- Format and lint your changes to ensure CI tests pass, using the following commands:
  ```bash
  make fmt
  make lint
  ```

## Pull Request process

1. Make desired changes
2. Commit the relevant files
3. Write a clear commit message
4. Open a [Pull Request](https://github.com/panther-labs/mcp-panther/pulls) against the `main` branch.
5. Once your PR has been approved by code owners, if you have merge permissions, merge it. If you do not have merge permissions, leave a comment requesting a code owner merge it for you

## Code of Conduct

Please follow the [Code of Conduct](https://github.com/panther-labs/mcp-panther/blob/main/CODE_OF_CONDUCT.md)
in all of your interactions with this project.

## Need help?

If you need assistance at any point, feel free to open a support ticket, or reach out to us on [Panther Community Slack](https://pnthr.io/community).

Thank you again for your contributions, and we look forward to working together!
