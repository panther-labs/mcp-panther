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

## Validation Guidelines

### What FastMCP/Pydantic Handles Automatically
- **Basic type validation**: `str`, `int`, `list[str]`, etc. are validated automatically
- **Field constraints**: `ge`, `le`, `min_length`, `max_length` work perfectly
- **List type validation**: `list[str]` automatically validates that all items are strings
- **Optional types**: `str | None` works correctly

### When to Use BeforeValidator
Only use `BeforeValidator` for:
- **Custom domain validation** - validating specific enum values (e.g., `["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]`)
- **Complex validation logic** - date format parsing, custom business rules
- **Value transformation** - converting or normalizing input values
- **Cross-field validation** - validating combinations of parameters

### When NOT to Use BeforeValidator
Avoid `BeforeValidator` for basic validation that Field constraints can handle:
- ❌ `_validate_positive_integer` → ✅ Use `Field(ge=1)`
- ❌ `_validate_non_empty_string` → ✅ Use `Field(min_length=1)`
- ❌ `_validate_string_list` → ✅ Use `list[str]` type hint

## Quick Reference: Annotated Tool Fields

Always use the `Annotated[Type, Field()]` pattern for all tool parameters:

```python
# Basic validation with Field constraints (preferred)
positive_int: Annotated[
    int,
    Field(ge=1, description="Must be positive integer"),
] = 1

# Complex validation requiring BeforeValidator
status: Annotated[
    str,
    BeforeValidator(_validate_alert_status),
    Field(
        description="Alert status", 
        examples=["OPEN", "TRIAGED", "RESOLVED", "CLOSED"]
    ),
]
```

See [@docs/mcp-development-best-practices.md](docs/mcp-development-best-practices.md#parameter-patterns) for complete parameter type patterns and guidelines.
