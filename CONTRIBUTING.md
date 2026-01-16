# Contributing to Manga Colorizer

Thank you for your interest in contributing to Manga Colorizer! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a branch: `git checkout -b feature/your-feature-name`
4. Make your changes
5. Test your changes
6. Commit and push
7. Create a Pull Request

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- Git

### Installation

```bash
# Clone repository
git clone <repository-url>
cd AIMangaColorer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Install pre-commit hooks
pre-commit install

# Install Node dependencies
npm install
```

### Development Dependencies

Create `requirements-dev.txt`:
```
pytest>=7.4.0
pytest-cov>=4.1.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
pre-commit>=3.3.0
```

## Code Style

### Python

- Follow PEP 8 style guide
- Use Black for formatting: `black backend/ cli/ tests/`
- Use type hints where appropriate
- Maximum line length: 100 characters

### JavaScript

- Use ES6+ syntax
- Use 4 spaces for indentation
- Use semicolons
- Use meaningful variable names

### Documentation

- Write clear docstrings for all public functions
- Include type hints in docstrings
- Update README.md when adding features

## Testing

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest --cov=backend tests/

# Run specific test file
python -m pytest tests/test_image_processor.py

# Run with verbose output
python -m pytest -v tests/
```

### Writing Tests

- Write tests for all new features
- Aim for >80% code coverage
- Use descriptive test names
- Include edge cases

Example test:
```python
import unittest
from backend.image_processor import ImageProcessor

class TestImageProcessor(unittest.TestCase):
    def setUp(self):
        self.processor = ImageProcessor()
    
    def test_resize_preserves_aspect_ratio(self):
        # Test implementation
        pass
```

## Commit Guidelines

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(cli): add support for custom model paths

fix(text-detector): improve speech bubble detection accuracy

docs(readme): update installation instructions for macOS
```

## Pull Request Process

1. **Update Documentation**: Update README.md, EXAMPLES.md, or other docs as needed

2. **Add Tests**: Include tests for new features or bug fixes

3. **Run Tests**: Ensure all tests pass
   ```bash
   python -m pytest tests/
   ```

4. **Format Code**: Run formatters
   ```bash
   black backend/ cli/ tests/
   ```

5. **Update Changelog**: Add entry to CHANGELOG.md (if it exists)

6. **Create PR**: 
   - Use a clear, descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include screenshots for UI changes

7. **Code Review**: Address reviewer feedback promptly

## Areas for Contribution

### High Priority

- [ ] Improve text detection accuracy
- [ ] Add support for more models
- [ ] Performance optimizations for MPS
- [ ] Better error handling and messages
- [ ] Additional test coverage

### Features

- [ ] Custom LoRA support
- [ ] Manual mask editing tool
- [ ] Batch style consistency
- [ ] GPU utilization monitoring
- [ ] Before/after comparison slider in GUI

### Documentation

- [ ] Video tutorials
- [ ] API documentation
- [ ] Architecture diagrams
- [ ] Performance benchmarks

### Testing

- [ ] Integration tests
- [ ] End-to-end tests for GUI
- [ ] Performance tests
- [ ] Cross-platform testing

## Code Review Guidelines

### For Reviewers

- Be respectful and constructive
- Focus on the code, not the person
- Explain reasoning behind suggestions
- Approve when ready, even if minor issues remain

### For Contributors

- Don't take feedback personally
- Ask questions if unclear
- Respond to all comments
- Update PR based on feedback

## Bug Reports

When reporting bugs, include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: Exact steps to reproduce the bug
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**:
   - OS and version
   - Python version
   - Relevant package versions
6. **Logs**: Error messages and stack traces
7. **Screenshots**: If applicable

## Feature Requests

When requesting features, include:

1. **Use Case**: Why is this feature needed?
2. **Description**: Detailed description of the feature
3. **Examples**: Examples of how it would work
4. **Alternatives**: Other solutions you considered
5. **Additional Context**: Any other relevant information

## Questions

For questions:
- Check existing documentation
- Search existing issues
- Ask in GitHub Discussions (if enabled)
- Create an issue with the "question" label

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

## Recognition

Contributors will be recognized in:
- README.md (for significant contributions)
- Release notes
- GitHub contributors page

## Getting Help

If you need help:
- Read the documentation (README.md, INSTALL.md, EXAMPLES.md)
- Check existing issues
- Create a new issue with details
- Be patient and respectful

## Code of Conduct

### Our Pledge

We pledge to make participation in our project a harassment-free experience for everyone.

### Our Standards

Examples of behavior that contributes to a positive environment:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints
- Gracefully accepting constructive criticism
- Focusing on what is best for the community

Examples of unacceptable behavior:
- Trolling, insulting/derogatory comments, and personal attacks
- Public or private harassment
- Publishing others' private information
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported by contacting the project team. All complaints will be reviewed and investigated.

---

Thank you for contributing to Manga Colorizer! 🎨
