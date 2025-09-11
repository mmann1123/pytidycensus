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

## Documentation Structure

```
docs/
├── conf.py              # Sphinx configuration
├── index.rst            # Main documentation page
├── getting_started.md   # Getting started guide
├── api/
│   ├── modules.rst      # API reference index
│   └── pytidycensus.rst # Auto-generated API docs
├── _static/             # Static files (CSS, images)
├── _templates/          # Custom templates
└── requirements.txt     # Documentation dependencies
```

## Configuration

### Sphinx Configuration (`conf.py`)

Key settings:
- **Theme**: `sphinx_rtd_theme` (Read the Docs theme)
- **Extensions**: Autodoc, Napoleon, MyST, etc.
- **Auto-generation**: Enabled for API documentation

### GitHub Actions Configuration

The workflow includes:
- **Caching**: Pip packages cached for faster builds
- **System deps**: Pandoc for MyST parsing
- **Verification**: Package import test before building
- **Conditional deployment**: Only deploys on main branch pushes

## Adding Documentation

### New Pages

1. Create `.md` or `.rst` files in the `docs/` directory
2. Add them to the `toctree` in `index.rst`
3. Use MyST markdown or reStructuredText format

### API Documentation

API docs are auto-generated from docstrings using:
- **Napoleon**: For Google/NumPy style docstrings
- **Autodoc**: For automatic module documentation
- **Type hints**: Displayed using `sphinx-autodoc-typehints`

### Examples and Notebooks

To add Jupyter notebooks:

1. Install `nbsphinx`: `pip install nbsphinx`
2. Add to `extensions` in `conf.py`
3. Place `.ipynb` files in docs directory
4. Reference in toctree

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