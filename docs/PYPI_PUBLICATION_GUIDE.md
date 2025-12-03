# PyPI Publication Guide for ka9q-python

## Executive Summary

**Yes, publishing to PyPI is strongly recommended** for `ka9q-python` (package name respects KA9Q callsign, import as `ka9q`). This package is:
- ✅ A dependency for multiple projects
- ✅ Already well-packaged and production-ready (v3.2.0)
- ✅ Properly configured with modern Python packaging standards
- ✅ Currently requires GitHub URL installation (suboptimal)

Publishing to PyPI will enable simple `pip install ka9q` instead of GitHub URL references.

## Why Publish to PyPI?

### Current Installation (GitHub)
```python
# requirements.txt
ka9q @ git+https://github.com/mijahauan/ka9q-python.git
```

**Problems:**
- Requires git to be installed
- Slower installation (clones entire repo)
- Version pinning is awkward (`@v3.2.0`)
- No automated dependency resolution
- Harder for users to discover

### With PyPI
```python
# requirements.txt
ka9q-python>=3.2.0
```

**Benefits:**
- ✅ Standard pip installation
- ✅ Proper version management
- ✅ Faster installation (pre-built wheels)
- ✅ Better dependency resolution
- ✅ Discoverable via PyPI search
- ✅ Professional credibility
- ✅ Automatic security scanning
- ✅ Download statistics

## Your Package Status

Your package is **publication-ready**:

```toml
[project]
name = "ka9q-python"
version = "3.2.0"
description = "Python interface for ka9q-radio control and monitoring"
requires-python = ">=3.9"
dependencies = ["numpy>=1.24.0"]
```

**Note:** Package name is `ka9q-python` (respecting KA9Q callsign), but import name remains `ka9q` (directory name unchanged).

- ✅ Modern `pyproject.toml` configuration (PEP 517/518)
- ✅ Proper package structure with `__init__.py`
- ✅ Comprehensive documentation (README.md)
- ✅ MIT License
- ✅ Version 3.2.0 (mature, stable)
- ✅ PyPI classifiers defined
- ✅ Examples and tests included

## Publication Process

### Step 1: Create PyPI Account

1. **Register at PyPI:**
   - Production: https://pypi.org/account/register/
   - Test (recommended first): https://test.pypi.org/account/register/

2. **Enable 2FA (Two-Factor Authentication)**
   - Required for new projects
   - Settings → Account security → Add 2FA

3. **Create API Token**
   - Settings → API tokens → Add API token
   - Scope: "Entire account" (first time) or "Project: ka9q" (later)
   - **Save the token** - shown only once!

### Step 2: Install Build Tools

```bash
cd /home/mjh/git/ka9q-python

# Install required tools
pip install --upgrade build twine

# Verify installation
python3 -m build --version
twine --version
```

### Step 3: Build Distribution Packages

```bash
# Clean any old builds
rm -rf dist/ build/ *.egg-info

# Build source distribution and wheel
python3 -m build

# This creates:
# - dist/ka9q_python-3.2.0.tar.gz (source)
# - dist/ka9q_python-3.2.0-py3-none-any.whl (wheel)
```

### Step 4: Test with TestPyPI (Recommended First!)

```bash
# Upload to test server
twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: pypi-... (your API token)
```

**Test the installation:**
```bash
# Create a test environment
python3 -m venv test_env
source test_env/bin/activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ka9q-python

# Test import
python3 -c "from ka9q import RadiodControl; print('Success!')"

# Clean up
deactivate
rm -rf test_env
```

### Step 5: Upload to Production PyPI

Once TestPyPI works:

```bash
# Upload to production PyPI
twine upload dist/*

# Username: __token__
# Password: pypi-... (your production API token)
```

### Step 6: Verify Publication

```bash
# Check PyPI page
# https://pypi.org/project/ka9q-python/

# Test installation
pip install ka9q-python

# Verify
python3 -c "import ka9q; print(ka9q.__version__)"
# Should print: 3.2.0
```

## Configuration for Easier Uploads

### Option A: Use `.pypirc` File (Convenient)

Create `~/.pypirc`:
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR_PRODUCTION_TOKEN_HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR_TEST_TOKEN_HERE
```

**Security:** Set proper permissions!
```bash
chmod 600 ~/.pypirc
```

Then upload without password prompt:
```bash
twine upload dist/*  # Uses [pypi] automatically
twine upload --repository testpypi dist/*  # Uses [testpypi]
```

### Option B: Environment Variables

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-YOUR_TOKEN_HERE
twine upload dist/*
```

### Option C: Command Line (Most Secure)

```bash
# Paste token when prompted
twine upload dist/*
```

## Future Releases

### Workflow for Updates

1. **Update version** in `pyproject.toml` and `ka9q/__init__.py`
2. **Update CHANGELOG.md** with changes
3. **Commit and tag:**
   ```bash
   git add pyproject.toml ka9q/__init__.py CHANGELOG.md
   git commit -m "Bump version to 3.3.0"
   git tag -a v3.3.0 -m "Release v3.3.0"
   git push origin main
   git push origin v3.3.0
   ```

4. **Build and upload:**
   ```bash
   rm -rf dist/
   python3 -m build
   twine upload dist/*
   ```

### Version Number Guidelines

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (3.x.x): Breaking API changes
- **MINOR** (x.3.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

Your current 3.2.0 suggests mature, stable API.

## Post-Publication Updates

### Update README.md

Your README already includes PyPI badge:
```markdown
[![PyPI version](https://badge.fury.io/py/ka9q.svg)](https://badge.fury.io/py/ka9q)
```

This will automatically show the version once published!

### Update Installation Instructions

Already correct in your README:
```bash
pip install ka9q
```

### Update Dependent Projects

In your other projects' `requirements.txt`:
```python
# Before (GitHub URL)
ka9q @ git+https://github.com/mijahauan/ka9q-python.git

# After (PyPI)
ka9q>=3.2.0
```

Or in `pyproject.toml`:
```toml
[project]
dependencies = [
    "ka9q>=3.2.0",
]
```

## Common Issues and Solutions

### Issue: "Invalid distribution filename"
**Solution:** Ensure version in `pyproject.toml` matches `ka9q/__init__.py`

### Issue: "Package already exists"
**Solution:** You can't re-upload the same version. Bump version number.

### Issue: "Invalid API token"
**Solution:** Make sure to use `__token__` as username (literal), not your PyPI username

### Issue: "File already exists"
**Solution:** Either:
- Delete files from PyPI (can only do within first hour)
- Create new version
- Use `--skip-existing` flag

### Issue: Upload fails with SSL error
**Solution:** Update certifi:
```bash
pip install --upgrade certifi
```

## Security Best Practices

1. **Never commit tokens** to git
2. **Use API tokens**, not passwords
3. **Scope tokens** to specific projects when possible
4. **Rotate tokens** periodically
5. **Enable 2FA** on PyPI account
6. **Use `.pypirc`** permissions: `chmod 600 ~/.pypirc`

## Maintenance Considerations

### PyPI Package Ownership

- You maintain full control
- Can add co-maintainers later
- Can transfer ownership if needed
- Can delete packages (with limitations)

### Yanking Bad Releases

If you release a broken version:
```bash
# Mark as "yanked" (users can still install with ==version, but won't get by default)
# Must do via PyPI web interface: Project → Manage → Yank release
```

### Monitoring

- Check PyPI stats: https://pypistats.org/packages/ka9q
- Monitor downloads
- Watch for issues on GitHub

## Recommended First Steps

1. **Test build locally:**
   ```bash
   rm -rf dist/
   python3 -m build
   ls -lh dist/
   ```

2. **Upload to TestPyPI** (practice)

3. **Test installation** from TestPyPI

4. **Upload to production PyPI**

5. **Update dependent projects** to use PyPI version

6. **Create GitHub release** matching PyPI version

## Complete Example Workflow

```bash
# One-time setup
pip install --upgrade build twine

# For each release
cd /home/mjh/git/ka9q-python

# 1. Update version (3.2.0 → 3.3.0)
# Edit: pyproject.toml, setup.py, ka9q/__init__.py, CHANGELOG.md

# 2. Clean and build
rm -rf dist/ build/ *.egg-info ka9q.egg-info/
python3 -m build

# 3. Check package
twine check dist/*

# 4. Test upload (optional but recommended)
twine upload --repository testpypi dist/*

# 5. Production upload
twine upload dist/*

# 6. Git tag
git add -A
git commit -m "Release v3.3.0"
git tag -a v3.3.0 -m "Release version 3.3.0"
git push origin main --tags

# 7. Verify
pip install --upgrade ka9q
python3 -c "import ka9q; print(ka9q.__version__)"
```

## Questions?

- **PyPI Documentation:** https://packaging.python.org/tutorials/packaging-projects/
- **Twine Documentation:** https://twine.readthedocs.io/
- **Packaging Guide:** https://packaging.python.org/

## Summary

✅ **Your package is ready** - All configuration complete  
✅ **Process is straightforward** - 5 steps, ~15 minutes first time  
✅ **Testing available** - TestPyPI lets you practice safely  
✅ **Benefits are significant** - Much better for users and dependent projects  
✅ **Recommendation: Publish to PyPI** - It's the standard way to distribute Python packages

You're in an excellent position to publish. The package is well-structured, documented, and mature at v3.2.0.
