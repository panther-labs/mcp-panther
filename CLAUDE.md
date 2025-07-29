# Code Guidelines

- Always use and commit changes in feature branches containing the human's git user
- Use the @Makefile commands for local linting, formatting, and testing
- Always update the __init__.py when adding new files for prompts, resources, or tools
- Always update the @README.md when adding or updating tool names, changing supported installations, and any user-facing information that's important. For developer-oriented instructions, update @src/README.md

## Development Documentation

For comprehensive development guidance, refer to:

- __[@docs/mcp-development-best-practices.md](docs/mcp-development-best-practices.md)__ - Core principles, parameter patterns, error handling, security practices
- __[@docs/mcp-testing-guide.md](docs/mcp-testing-guide.md)__ - Testing strategies and patterns  
- __[@docs/tool-design-patterns.md](docs/tool-design-patterns.md)__ - Tool design patterns and anti-patterns
- __[@docs/server-architecture-guide.md](docs/server-architecture-guide.md)__ - Server architecture and context management

## Quick Reference: Annotated Tool Fields

Always use the `Annotated[Type, Field()]` pattern for all tool parameters:

```python
param_name: Annotated[
    Type | None,  # or just Type for required params
    Field(
        description="Clear description of the parameter",
        examples=["example1", "example2"],  # when helpful
    ),
] = default_value
```

See [@docs/mcp-development-best-practices.md](docs/mcp-development-best-practices.md#parameter-patterns) for complete parameter type patterns and guidelines.
