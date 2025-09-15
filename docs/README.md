# Documentation Setup Guide

This directory contains the Sphinx documentation for pytidycensus.

## Automatic Documentation Deployment

The documentation is automatically built and deployed to GitHub Pages when changes are merged to the `main` branch via GitHub Actions.

### GitHub Actions Workflow

The `.github/workflows/docs.yml` workflow:

1. **Triggers**: Runs on pushes and pull requests to `main`/`master` branches
2. **Builds**: Compiles Sphinx documentation from source
3. **Deploys**: Publishes to GitHub Pages (only on pushes to main)

### Setting Up GitHub Pages

To enable automatic documentation deployment:

1. Go to your repository's **Settings** > **Pages**
2. Under **Source**, select **GitHub Actions**
3. The workflow will automatically deploy docs on the next push to main

## Local Documentation Building

### Prerequisites

```bash
# Install documentation dependencies
pip install -e .[docs]

# Or install requirements directly
pip install -r docs/requirements.txt
```

### Building Locally

```bash
# Navigate to docs directory
cd docs

# Clean previous builds
rm -rf _build

# Build HTML documentation
sphinx-build -b html . _build/html

# Build with warnings as errors (same as CI)
sphinx-build -b html -W --keep-going . _build/html

# Serve locally (optional)
python -m http.server 8000 -d _build/html
```

Then open http://localhost:8000 in your browser.

### Live Reload (Development)

For live reloading during development:

```bash
pip install sphinx-autobuild
sphinx-autobuild docs docs/_build/html
```

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure package is properly installed (`pip install -e .`)
2. **Missing dependencies**: Install docs requirements (`pip install -e .[docs]`)
3. **Build warnings**: Check docstring formatting and cross-references
4. **GitHub Pages not updating**: Check Actions tab for workflow status

### Testing Locally

```bash
# Test that docs build without warnings
sphinx-build -b html -W docs docs/_build/html

# Check for broken links
sphinx-build -b linkcheck docs docs/_build/linkcheck

# Test package imports
python -c "import pytidycensus; print('OK')"
```

## Deployment URLs

- **GitHub Pages**: `https://<username>.github.io/<repository>/`
- **Read the Docs**: `https://pytidycensus.readthedocs.io/` (if configured)

The documentation will be automatically available at the GitHub Pages URL after the first successful deployment.

## Come study with us at The George Washington University

![GWU Geography & Environment](static/GWU_GE.png)