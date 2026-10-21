---
layout: default
title: Contributing
has_children: true
nav_order: 2
---


# Contributing

This project welcomes contributions from the community. There are 3 main aspects to the project:

- Hardware, the TUSS4470 shields which can be used to drive transducers
- Firmware, written in arduino IDE and uploaded to various microcontroller boards (which the TUSS4470 shields connect to)
- Software, python code for viewing the outputs from the firmware/hardware (in future also to be used for configuring them!)

## Firmware

### Prerequisites
- Git
- Arduino IDE (or VSCode with Arduino Community extension)

### Getting started
1. Clone the repository
2. Open arduino IDE (or VSCode with Arduino community extension) the sketch for the board you are planning to develop for
3. Select your board - you may need to install the relevant library.
4. Make your changes
5. Upload the sketch!

## Python Software

### Prerequisites
- Git
- Python (installed on your system)
- uv (see install instructions: https://docs.astral.sh/uv/)

### Getting started
1. Clone the repository
2. Set up the environment and install dependencies:
    ```
    uv sync
    ```
    This will create a virtual environment and install dependencies defined in pyproject.toml.

### Git hooks
The repository provides optional Git hooks to run typechecks, linting and unit tests:

```
git config core.hooksPath .githooks
chmod +x .githooks/*
```

If you want to commit without these checks (e.g. when you haven't written unit tests yet!) you can use `git commit --no-verify`

### Formatting, linting, typecheck and test
- Format:
  ```
  uvx ruff format
  ```
- Lint and auto-fix:
  ```
  uvx ruff check --fix
  ```
- Typecheck:
  ```
  uv run mypy
  ```
- Unit test
  ```
  uv run pytest
  ```

## Contribution workflow
- Fork and create a new branch for your changes.
- Keep commits focused and descriptive.
- Ensure formatting, linting, and tests pass before opening a pull request.
- Submit a PR with a clear summary of changes and any relevant context.

Thank you for contributing.