# PyPI Quick Start Checklist

## ✅ Pre-Publication Checklist

Your package status (already complete):
- [x] Package name: `ka9q-python` (respects KA9Q callsign, import as `ka9q`)
- [x] Version: 3.2.0 (mature)
- [x] `pyproject.toml` configured
- [x] `setup.py` present (backward compatibility)
- [x] `README.md` comprehensive
- [x] `LICENSE` file (MIT)
- [x] Proper package structure (`ka9q/__init__.py`)
- [x] Dependencies declared (`numpy>=1.24.0`)
- [x] Examples included
- [x] Tests written

**Status: Ready to publish! 🚀**

## 🎯 First-Time Publication (15 minutes)

### 1. Create PyPI Accounts (5 min)
```bash
# Register at:
# Test: https://test.pypi.org/account/register/
# Prod: https://pypi.org/account/register/

# Enable 2FA (required)
# Create API tokens (save them!)
```

### 2. Install Tools (1 min)
```bash
pip install --upgrade build twine
```

### 3. Build Package (1 min)
```bash
cd /home/mjh/git/ka9q-python
rm -rf dist/ build/ *.egg-info
python3 -m build
```

### 4. Test Upload (3 min)
```bash
# Upload to test server
twine upload --repository testpypi dist/*
# Username: __token__
# Password: <paste your TestPyPI token>

# Test install
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ ka9q-python
```

### 5. Production Upload (2 min)
```bash
twine upload dist/*
# Username: __token__
# Password: <paste your PyPI token>
```

### 6. Verify (3 min)
```bash
# Check: https://pypi.org/project/ka9q-python/
pip install ka9q-python
python3 -c "import ka9q; print(ka9q.__version__)"  # Import name is 'ka9q'
```

## 🔄 Future Releases (5 minutes)

```bash
# 1. Update version in:
#    - pyproject.toml (line 7)
#    - setup.py (line 15)
#    - ka9q/__init__.py (line 25)
#    - CHANGELOG.md

# 2. Build
rm -rf dist/
python3 -m build

# 3. Upload
twine upload dist/*

# 4. Tag and push
git commit -am "Release v3.3.0"
git tag v3.3.0
git push origin main --tags
```

## 🔐 Save API Token (Optional but Convenient)

Create `~/.pypirc`:
```ini
[pypi]
username = __token__
password = pypi-YOUR_TOKEN_HERE
```

Set permissions:
```bash
chmod 600 ~/.pypirc
```

Then upload without password prompt:
```bash
twine upload dist/*
```

## 💡 What Changes for Your Users

### Before (GitHub install)
```bash
pip install git+https://github.com/mijahauan/ka9q-python.git
```

### After (PyPI install)
```bash
pip install ka9q-python
```

### In requirements.txt

Before:
```
ka9q @ git+https://github.com/mijahauan/ka9q-python.git
```

After:
```
ka9q-python>=3.2.0
```

## 🎓 Key Concepts

- **TestPyPI:** Practice server, same interface as production
- **Twine:** Tool for uploading to PyPI (secure, validates packages)
- **Build:** Creates source distribution (.tar.gz) and wheel (.whl)
- **API Token:** Use `__token__` as username, token as password
- **Version:** Can't re-upload same version, must increment

## 🚨 Common First-Time Mistakes

1. ❌ Using PyPI username instead of `__token__`
2. ❌ Trying to upload same version twice
3. ❌ Forgetting to build after version change
4. ❌ Not enabling 2FA (required for new projects)
5. ❌ Committing API tokens to git

## 📊 After Publication

**Your package will be:**
- Searchable on PyPI: https://pypi.org/project/ka9q-python/
- Installable via `pip install ka9q-python`
- Importable as: `import ka9q`
- Version-pinnable: `ka9q-python==3.2.0` or `ka9q-python>=3.2.0`
- Discoverable by the community
- Tracked on pypistats.org

**Your README badge will work:**
```markdown
[![PyPI version](https://badge.fury.io/py/ka9q-python.svg)](https://badge.fury.io/py/ka9q-python)
```

## 🤝 Why This Matters

You mentioned this package is:
> "a requirement for several projects that need to interact with radiod"

**Publishing to PyPI means:**
- ✅ Your dependent projects get simpler installation
- ✅ Version management becomes standard
- ✅ Other users can easily discover and use your work
- ✅ Professional credibility and visibility
- ✅ Proper dependency resolution

## 📚 Full Documentation

See `docs/PYPI_PUBLICATION_GUIDE.md` for complete details, troubleshooting, and security best practices.

## Ready to Publish?

```bash
# Quick start
pip install --upgrade build twine
python3 -m build
twine upload --repository testpypi dist/*  # Test first
twine upload dist/*                        # Then production
```

**Good luck! 🚀**
