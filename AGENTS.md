# Instructions for AI Contributors

This repository contains a Django project. When modifying any code or documentation, follow these guidelines:

## Testing

- When modifying or adding code, always write corresponding tests.
- Run the Django test suite with:
  ```bash
  /Users/ali/codes/sentryHub/venv/bin/python3 manage.py test
  ```
  If that path does not exist, fall back to `python3 manage.py test`.

## Code Style

- Follow PEP8 style for Python code.
- Keep changes focused and consistent with the existing project structure described in the `.clinerules` directory.

## Commits and Pull Requests

- Write concise commit messages describing the change.
- Provide a brief PR title and description summarizing what was done and any relevant test results.

