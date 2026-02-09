# Contributing to Real-Time Recommender MLOps

First off, thank you for considering contributing to this project! 🎉

## How Can I Contribute?

### 🐛 Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the behavior
- **Expected behavior** vs actual behavior
- **Screenshots** if applicable
- **Environment details** (OS, Docker version, etc.)

**Example:**
```markdown
## Bug: Frontend dashboard not loading

**Steps to reproduce:**
1. Run `docker-compose up -d`
2. Navigate to http://localhost:3000
3. See blank screen

**Expected:** Dashboard with metrics
**Actual:** White screen

**Environment:** Windows 11, Docker 24.0.7
```

### 💡 Suggesting Features

Feature requests are welcome! Please provide:

- **Clear use case**: Why is this feature needed?
- **Proposed solution**: How should it work?
- **Alternatives considered**: Other approaches you've thought about

### 🔧 Pull Requests

1. **Fork** the repo and create your branch from `main`
2. **Make your changes** with clear, descriptive commits
3. **Test** your changes thoroughly
4. **Update documentation** if needed
5. **Submit** a pull request

#### Pull Request Guidelines

- ✅ One feature/fix per PR
- ✅ Follow existing code style
- ✅ Add tests for new features
- ✅ Update README if needed
- ✅ Keep PRs focused and small

#### Commit Message Format

```
feat: add dark mode toggle to dashboard
fix: resolve Redis connection timeout
docs: update installation instructions
perf: optimize FAISS vector search
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

### 🧪 Testing

Before submitting PR, run tests:

```bash
# Backend tests
python test_system.py
python test_backend_api.py

# Frontend tests
cd frontend && npm test

# Integration tests
python test_phase3_dynamic.py
```

### 📝 Code Style

**Python:**
- Follow PEP 8
- Use type hints
- Add docstrings for functions
- Max line length: 100 characters

**TypeScript/React:**
- Use functional components
- Follow React hooks best practices
- Use TypeScript types (no `any`)
- Use Prettier for formatting

**Example Python:**
```python
def get_recommendations(
    user_id: int,
    top_k: int = 10,
    exclude_seen: bool = True
) -> List[Recommendation]:
    """
    Generate personalized recommendations for a user.
    
    Args:
        user_id: Unique user identifier
        top_k: Number of recommendations to return
        exclude_seen: Whether to exclude previously seen items
        
    Returns:
        List of Recommendation objects sorted by score
    """
    # Implementation
```

### 🌳 Branch Naming

- `feature/add-neural-cf` - New features
- `fix/redis-timeout` - Bug fixes
- `docs/update-readme` - Documentation
- `refactor/api-structure` - Code refactoring

### 📦 Areas for Contribution

#### High Priority
- [ ] Add unit tests for recommendation service
- [ ] Implement Kubernetes deployment configs
- [ ] Add CI/CD pipeline (GitHub Actions)
- [ ] Improve error handling and logging
- [ ] Add load testing suite

#### Medium Priority
- [ ] Multi-armed bandit optimization
- [ ] Neural collaborative filtering model
- [ ] Real-time feature engineering pipeline
- [ ] Advanced A/B testing (multi-variant)
- [ ] Monitoring alerts and notifications

#### Good First Issues
- [ ] Add environment variable validation
- [ ] Improve error messages
- [ ] Add more API examples to docs
- [ ] Create Docker health check scripts
- [ ] Add configuration templates

### 🎨 UI/UX Improvements

- Dark mode enhancements
- Mobile responsiveness
- Accessibility (WCAG compliance)
- Loading states and animations
- Chart customization options

### 📚 Documentation

- Add architecture diagrams
- Create video tutorials
- Write deployment guides
- Document API endpoints
- Add troubleshooting FAQs

## Development Setup

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/realtime-recommender-mlops.git
cd realtime-recommender-mlops

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# 3. Install dependencies
pip install -r requirements.txt
cd frontend && npm install

# 4. Create feature branch
git checkout -b feature/your-feature-name

# 5. Make changes and test
# ... make your changes ...
python test_system.py

# 6. Commit and push
git add .
git commit -m "feat: add your feature"
git push origin feature/your-feature-name

# 7. Create Pull Request on GitHub
```

## Code Review Process

1. **Automated Checks**: CI runs tests automatically
2. **Human Review**: Maintainers review code
3. **Feedback**: Address any comments or requests
4. **Merge**: Once approved, PR is merged

**Review Time:** Usually within 2-3 days

## Community Guidelines

- Be respectful and inclusive
- Welcome newcomers
- Provide constructive feedback
- Follow [Code of Conduct](CODE_OF_CONDUCT.md)

## Recognition

Contributors will be:
- Listed in README contributors section
- Mentioned in release notes
- Given credit in documentation

## Questions?

- 💬 Open a [Discussion](https://github.com/yourusername/realtime-recommender-mlops/discussions)
- 📧 Contact maintainers
- 📖 Check existing [Issues](https://github.com/yourusername/realtime-recommender-mlops/issues)

---

**Thank you for contributing! 🚀**
