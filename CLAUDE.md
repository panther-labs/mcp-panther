# Code Guidelines

- Always use and commit changes in feature branches containing the human's git user
- Use the @Makefile commands for local linting, formatting, and testing
- Always update the __init__.py when adding new files in prompts, resources, or tools
- Always update the @README.md when adding or updating tools, changing supported installations, and any user-facing information that's important. For developer-oriented instructions, update @src/README.md
- When using Annotated args, always use the Field object with a description, declare examples, a default value with | but DO NOT use Literals or Enums for objects (these have mixed results with AI tools like Claude and Goose)