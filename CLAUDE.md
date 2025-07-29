# Code Guidelines

- Always use and commit changes in feature branches containing the human's git user
- Use the @Makefile commands for local linting, formatting, and testing
- Always update the __init__.py when adding new files for prompts, resources, or tools
- Always update the @README.md when adding or updating tool names, changing supported installations, and any user-facing information that's important. For developer-oriented instructions, update @src/README.md

## Annotated Tool Field Best Practices

When defining tool parameters, always use the `Annotated` pattern with
`Field()` objects:

### Core Pattern Structure

```python
param_name: Annotated[
    Type | None,  # or just Type for required params
    Field(
        description="Clear description of the parameter",
        examples=["example1", "example2"],  # when helpful
    ),
] = default_value
```

#### Parameter Type Patterns

Optional String Parameters:

```python
cursor: Annotated[
    str | None,
    Field(description="Optional cursor for pagination from a previous query"),
] = None
```

Boolean Parameters with Meaningful Defaults:

```python
is_healthy: Annotated[
    bool,
    Field(description="Filter by health status (default: True)"),
] = True
```

Prefer concrete defaults over None when the meaning is clear:

```python
is_archived: Annotated[
    bool,
    Field(description="Filter by archive status (default: False shows 
non-archived)"),
] = False
```

List Parameters with Empty Defaults:

```python
log_types: Annotated[
    list[str],
    Field(
        description="Optional list of log types to filter by",
        examples=[["AWS.CloudTrail", "AWS.S3ServerAccess"]],
    ),
] = []
```

Required Parameters (No Default):

```python
user_id: Annotated[
    str,
    Field(
        description="The ID of the user to fetch",
        examples=["user-123"],
    ),
]
```

String Parameters with Specific Defaults:

```python
sort_dir: Annotated[
    str | None,
    Field(
        description="The sort direction for the results",
        examples=["asc", "desc"]
    ),
] = "asc"
```

### Guidelines

1. Always use `Field()` with descriptive text - never rely on parameter names
alone
2. Include `examples=[]` for complex parameters - especially lists, enums, and
structured data
3. Use meaningful defaults instead of None when possible:
    - `[]` for lists that should be empty by default
    - `False/True` for boolean filters with clear default behavior
    - Specific string values when there's a sensible default
4. Consistent type patterns: `str | None, list[str], dict[str, Any]`
5. Never use `Literals` or `Enums` - they have mixed results with AI tools
6. Description should explain the parameter's purpose and default behavior
