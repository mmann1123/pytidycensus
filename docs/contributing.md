# Contributing to pytidycensus

Thank you for your interest in contributing to pytidycensus! This document provides guidelines for contributing to the project.

## Getting Started

### Development Setup

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/yourusername/pytidycensus.git
   cd pytidycensus
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install in development mode**:
   ```bash
   pip install -e ".[dev,docs,test]"
   ```

4. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

### Running Tests

Run the test suite with:
```bash
pytest
```

For coverage reporting:
```bash
pytest --cov=pytidycensus
```

### Building Documentation

Build the documentation locally:
```bash
cd docs
sphinx-build -b html . _build/html
```

## Code Style

- Follow [PEP 8](https://pep8.org/) Python style guidelines
- Use type hints where appropriate
- Write docstrings for all public functions following Google style
- Keep line length to 100 characters

## Testing

- Write tests for all new functionality
- Maintain or improve code coverage
- Use pytest fixtures for common test data
- Mock external API calls in tests

## Documentation

- Update docstrings for any changed functions
- Add examples to docstrings when helpful
- Update relevant notebook examples if functionality changes
- Ensure documentation builds without warnings

## Submitting Changes

### Pull Request Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes and commit**:
   ```bash
   git add .
   git commit -m "Add descriptive commit message"
   ```

3. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

4. **Create a pull request** on GitHub

### Pull Request Guidelines

- **Clear description**: Explain what changes you made and why
- **Link issues**: Reference any related GitHub issues
- **Test coverage**: Ensure tests pass and coverage is maintained
- **Documentation**: Update docs if needed
- **Changelog**: Add entry to `changelog.md` for user-facing changes

## Types of Contributions

### Bug Reports

When reporting bugs, please include:
- Python version and operating system
- Minimal code example that reproduces the issue
- Full error traceback
- Expected vs. actual behavior

### Feature Requests

For new features:
- Describe the use case and motivation
- Provide examples of how it would be used
- Consider backwards compatibility
- Be open to discussion about implementation

### Code Contributions

We welcome:
- Bug fixes
- New Census datasets support
- Performance improvements
- Documentation improvements
- Test coverage improvements
- New examples or tutorials

## Census API Guidelines

When working with Census APIs:
- Respect rate limits and implement appropriate throttling
- Handle API errors gracefully
- Cache responses when appropriate
- Test with both valid and invalid inputs
- Follow Census Bureau's terms of service

## Example Contributions

We especially welcome:
- New Jupyter notebook examples
- Tutorials for specific use cases
- Real-world data analysis examples
- Geographic analysis workflows

## Questions?

- Open an issue for questions about contributing
- Check existing issues and documentation first
- Be respectful and constructive in discussions

## Code of Conduct

This project follows a code of conduct based on the [Contributor Covenant](https://www.contributor-covenant.org/). 
Be respectful, inclusive, and constructive in all interactions.

## Recognition

Contributors will be acknowledged in the documentation and release notes. 
Thank you for helping make pytidycensus better!

## Come study with us at The George Washington University

![GWU Geography & Environment](static/GWU_GE.png)