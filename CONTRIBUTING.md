# Contributing to Agent Trust Stack

Thank you for your interest in contributing to Agent Trust Stack!

## 🤝 How to Contribute

### Reporting Issues

We use GitHub Issues for bug reports and feature requests. Before creating a new issue:

1. Check existing issues to avoid duplicates
2. Use the appropriate issue template
3. Provide as much detail as possible

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-org/agent-trust-stack.git
cd agent-trust-stack

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check src/
black src/
mypy src/
```

### Code Style

We use:
- **Black** for code formatting
- **Ruff** for linting
- **mypy** for type checking
- **pytest** for testing

### Commit Messages

Follow conventional commits format:

```
feat: add new feature
fix: resolve issue #123
docs: update README
test: add tests for identity module
chore: update dependencies
```

## 📋 Areas for Contribution

### High Priority
- [ ] Implement actual liboqs integration in crypto.py
- [ ] Add comprehensive test coverage (target: 85%+)
- [ ] Implement key rotation with grace period
- [ ] Add revocation system using cryptographic accumulators

### Medium Priority
- [ ] Implement zero-knowledge proofs for selective disclosure
- [ ] Add Sybil detection algorithms
- [ ] Create integration tests
- [ ] Add more examples and tutorials

### Low Priority
- [ ] Mobile SDKs (iOS, Android)
- [ ] WebAssembly bindings
- [ ] Admin tools and dashboards
- [ ] Performance optimizations

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

## 📞 Contact

For questions, please open an issue or start a discussion.
