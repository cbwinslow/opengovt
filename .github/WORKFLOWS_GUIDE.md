# GitHub Actions Workflows Guide

This document provides a comprehensive overview of all automated workflows in this repository.

## Table of Contents

- [Overview](#overview)
- [Workflow Categories](#workflow-categories)
- [Configuration Requirements](#configuration-requirements)
- [Workflow Details](#workflow-details)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Overview

This repository uses **12 comprehensive GitHub Actions workflows** with **20+ marketplace integrations** to ensure code quality, security, documentation, and maintainability.

### Quick Stats
- 🔄 **12** custom workflow files
- 🛠️ **20+** GitHub Marketplace actions
- 🤖 **9** AI-powered agents (CrewAI)
- 🔒 **6** security scanning tools
- 📊 **5** code quality tools
- 📝 **4** documentation generators

## Workflow Categories

### 1. Code Quality & Linting
**File:** `.github/workflows/code-quality.yml`

**Purpose:** Comprehensive code quality checks across all languages

**Features:**
- Super-Linter for all file types
- Python: Black, Flake8, Pylint, isort, MyPy, Bandit
- JavaScript/TypeScript: ESLint, Prettier, TypeScript checking
- Go: golangci-lint, go vet, staticcheck
- SQL: sqlfluff
- Code complexity analysis

**Triggers:** Push to main/develop, Pull requests

**Usage:**
```bash
# Run locally before pushing
black .
flake8 .
npx eslint .
npx prettier --write .
```

### 2. File Header Management
**File:** `.github/workflows/file-header-management.yml`

**Purpose:** Automatically add standardized headers to files

**Features:**
- Detects files without headers
- Generates appropriate headers based on file type
- Includes: name, description, inputs, outputs, usage, date, changelog
- Creates PR with changes or comments on existing PR

**Triggers:** Push, Pull requests, Weekly schedule, Manual dispatch

**Example Header:**
```python
"""
filename.py

Description:
    Brief description of the file

Inputs:
    Command-line arguments, environment variables

Outputs:
    Console output, log files, or data files

Usage:
    python filename.py

Author: Auto-generated
Date: 2025-01-23
Last Modified: 2025-01-23

Changelog:
    - 2025-01-23: Initial header creation
"""
```

### 3. Dependency Management
**Files:** 
- `.github/dependabot.yml`
- `.github/workflows/dependency-review.yml`

**Purpose:** Automated dependency updates and security scanning

**Features:**
- **Dependabot:** Weekly updates for npm, pip, Go modules, GitHub Actions, Docker
- **NPM Audit:** Security vulnerabilities in npm packages
- **pip-audit:** Python package vulnerabilities
- **Safety:** Python dependency security checks
- **Snyk:** Cross-platform vulnerability scanning
- **OSV Scanner:** Open Source Vulnerabilities
- **License Compliance:** Verify compatible licenses

**Triggers:** Pull requests, Push, Weekly schedule

**Configuration:**
- Update schedule: Weekly on Monday at 3 AM
- Max open PRs: 10 for npm/pip, 5 for others
- Auto-assigned to: cbwinslow

### 4. Advanced Security Scanning
**Files:**
- `.github/workflows/codeql-advanced.yml`
- `.github/workflows/secrets-scanning.yml`

**Purpose:** Multi-layered security analysis

**Features:**

**CodeQL Analysis:**
- JavaScript, Python, Go analysis
- Security and quality queries
- SARIF upload to Security tab

**Semgrep:**
- Static analysis security tool
- Custom rule configurations

**Secrets Detection:**
- TruffleHog OSS
- Gitleaks
- Detect-secrets
- GitGuardian
- Custom pattern matching (AWS keys, DB strings, JWT tokens, etc.)

**Triggers:** Push, Pull requests, Weekly schedule

**Alert Locations:**
- GitHub Security tab
- Workflow artifacts
- PR comments

### 5. Code Formatting
**File:** `.github/workflows/code-formatting.yml`

**Purpose:** Automated code formatting and style enforcement

**Features:**
- **Python:** Black (formatting), isort (imports)
- **JavaScript/TypeScript:** Prettier
- **Go:** gofmt, goimports
- Auto-commits to non-PR branches
- Comments on PRs with formatting issues

**Triggers:** Push, Pull requests, Manual dispatch

**Configuration Files:**
- `.prettierrc.json` - Prettier settings
- `.eslintrc.json` - ESLint rules
- `pyproject.toml` - Black, isort settings

### 6. Database & SQL Validation
**File:** `.github/workflows/database-validation.yml`

**Purpose:** Database schema and SQL quality checks

**Features:**
- SQL linting with sqlfluff (PostgreSQL dialect)
- Database model validation
- PostgreSQL connection testing
- Migration file detection
- SQL syntax validation in Python files
- Data model documentation generation

**Triggers:** Push/PR on SQL files, models, db directories, Manual dispatch

**Requirements:**
- PostgreSQL test database (provided by workflow)
- psycopg2-binary, sqlalchemy

### 7. Code Maintenance
**File:** `.github/workflows/code-maintenance.yml`

**Purpose:** Code health monitoring and cleanup suggestions

**Features:**
- **Dead Code Detection:** vulture
- **Duplicate Code:** pylint, jscpd
- **Code Metrics:** Cyclomatic complexity, maintainability index, Halstead metrics
- **Unused Dependencies:** depcheck (npm), autoflake (Python)
- **TODO Tracking:** Find all TODO, FIXME, XXX, HACK comments
- **Code Churn:** Most frequently changed files
- **Dependency Updates:** Check for available updates

**Triggers:** Weekly schedule (Thursday 7 AM), Push, Manual dispatch

**Reports Generated:**
- Dead code report
- Duplicate code report
- Code metrics report
- TODO comments report
- Code churn report

### 8. Documentation Generation
**File:** `.github/workflows/documentation-generation.yml`

**Purpose:** Automated documentation creation and updates

**Features:**
- **API Docs:** pdoc3 (Python), TypeDoc (TypeScript), JSDoc (JavaScript), godoc (Go)
- **Function Docs:** From generate_docs.py script
- **README Stats:** Repository statistics
- **Changelog:** Automated with git-cliff
- **Architecture Diagrams:** Dependency graphs
- **Coverage Checks:** Docstring coverage with interrogate
- **Link Validation:** Markdown link checking
- **Spell Check:** Documentation spell checking
- **Contributor Docs:** Contributor statistics

**Triggers:** Push on code files, Pull requests, Weekly schedule (Friday 8 AM), Manual dispatch

**Outputs:**
- `docs/api/` - Generated API documentation
- `CHANGELOG.md` - Auto-generated changelog
- `CONTRIBUTORS.md` - Contributor list

### 9. Advanced CrewAI Agents
**File:** `.github/workflows/crewai-advanced-agents.yml`

**Purpose:** AI-powered code analysis and improvement

**Features - Individual Agents:**
1. **Code Review Agent:** Comprehensive code review
2. **Test Generation Agent:** Generate unit, integration, e2e tests
3. **Documentation Agent:** Create technical documentation
4. **Security Audit Agent:** Identify vulnerabilities
5. **Performance Optimization Agent:** Performance improvements
6. **Bug Detection Agent:** Find potential bugs
7. **Code Explanation Agent:** Explain complex code
8. **Architecture Analysis Agent:** System design review
9. **Database Optimization Agent:** DB query optimization

**Multi-Agent Collaboration:**
- Architect + Reviewer + Security working together
- Comprehensive analysis reports

**Triggers:** Manual dispatch (select agent), Weekly schedule (Saturday 9 AM)

**Requirements:**
- `OPENROUTER_API_KEY` or `LOCALAI_BASE_URL` secret
- CrewAI, langchain dependencies

**Usage:**
```yaml
# Run via workflow dispatch
# Select agent_task: code-review-agent
# Optional: specify target_files
```

### 10. File Organization
**File:** `.github/workflows/file-organization.yml`

**Purpose:** Repository structure analysis and suggestions

**Features:**
- Structure analysis (file types, sizes, distribution)
- Directory tree generation
- Naming convention checks
- Organization suggestions
- File permission checks
- Duplicate file detection
- Structure documentation (STRUCTURE.md)

**Triggers:** Weekly schedule (Sunday 10 AM), Push, Manual dispatch

**Outputs:**
- Repository structure report
- File organization suggestions
- `STRUCTURE.md` - Auto-generated structure doc

### 11. Marketplace Integrations
**File:** `.github/workflows/marketplace-integrations.yml`

**Purpose:** Integration with free GitHub marketplace actions

**Features:**

**Code Quality:**
- Codecov (coverage)
- CodeFactor
- SonarCloud
- DeepSource

**Automation:**
- Stale issue/PR management
- Auto-labeling (by file type)
- PR size labeling
- TODO to Issue conversion
- Auto-assign reviewers
- First-time contributor welcome

**Performance:**
- Lighthouse CI
- Compressed size checking
- Bundle size analysis

**Metrics:**
- Issue metrics
- Contributor statistics
- Repository visualization

**Triggers:** Push, Pull requests, Daily schedule (2 AM)

## Configuration Requirements

### Required Secrets

Add these secrets in GitHub Settings → Secrets and variables → Actions:

#### AI/Analysis (Optional but recommended)
- `OPENROUTER_API_KEY` - For AI agents
- `LOCALAI_BASE_URL` - Alternative local AI endpoint

#### Code Quality (Optional)
- `CODECOV_TOKEN` - Codecov integration
- `CODEFACTOR_TOKEN` - CodeFactor integration
- `SONAR_TOKEN` - SonarCloud integration
- `DEEPSOURCE_DSN` - DeepSource integration

#### Security (Optional)
- `SNYK_TOKEN` - Snyk security scanning
- `GITGUARDIAN_API_KEY` - GitGuardian secrets detection
- `GITLEAKS_LICENSE` - Gitleaks enterprise features

**Note:** Most workflows work without secrets but have reduced functionality

### Configuration Files

Already created and configured:
- `.prettierrc.json` - Prettier formatting
- `.eslintrc.json` - ESLint rules
- `pyproject.toml` - Python tools (Black, isort, Pylint, MyPy)
- `.github/dependabot.yml` - Dependency updates
- `.github/labeler.yml` - Auto-labeling rules
- `.github/markdown-link-check.json` - Link validation
- `.github/spellcheck-config.yml` - Spell checking

## Best Practices

### For Contributors

1. **Before Committing:**
   ```bash
   # Format code
   black .
   isort .
   npx prettier --write .
   
   # Run linters
   flake8 .
   npx eslint .
   
   # Run tests
   npm test
   ```

2. **Understanding Workflow Failures:**
   - Check workflow logs in Actions tab
   - Review artifact reports
   - Fix issues locally before pushing

3. **Working with AI Agents:**
   - Use workflow dispatch to run specific agents
   - Review AI suggestions carefully
   - Test AI-generated code thoroughly

### For Maintainers

1. **Managing Dependabot:**
   - Review and merge dependency PRs regularly
   - Configure auto-merge for patch updates
   - Test major version updates carefully

2. **Monitoring Security:**
   - Check Security tab weekly
   - Review SARIF uploads
   - Respond to vulnerability alerts promptly

3. **Documentation Maintenance:**
   - Let workflows generate docs automatically
   - Review and supplement auto-generated content
   - Keep WORKFLOWS_GUIDE.md updated

## Troubleshooting

### Common Issues

#### Workflow Fails Due to Missing Dependencies
**Solution:** Install dependencies in workflow or update requirements.txt

#### CodeQL Analysis Times Out
**Solution:** Already configured to skip large directories. Adjust paths-ignore if needed.

#### AI Agents Fail
**Solution:** Ensure API keys are configured. Agents require OPENROUTER_API_KEY or LOCALAI_BASE_URL.

#### Linting Fails on Existing Code
**Solution:** Workflows use `|| true` for existing code. Fix issues incrementally.

#### Too Many Dependabot PRs
**Solution:** Adjust `open-pull-requests-limit` in .github/dependabot.yml

### Getting Help

1. Check workflow logs in Actions tab
2. Review artifact reports for detailed analysis
3. Check SARIF files in Security tab
4. Review PR comments from workflow bots
5. Open an issue with workflow logs

## Workflow Triggers Summary

| Workflow | Push | PR | Schedule | Manual |
|----------|------|-----|----------|--------|
| Code Quality | ✅ | ✅ | ❌ | ❌ |
| File Headers | ✅ | ✅ | ✅ Weekly | ✅ |
| Dependencies | ✅ | ✅ | ✅ Weekly | ❌ |
| Security | ✅ | ✅ | ✅ Weekly | ❌ |
| Formatting | ✅ | ✅ | ❌ | ✅ |
| Database | ✅ | ✅ | ❌ | ✅ |
| Maintenance | ✅ | ❌ | ✅ Weekly | ✅ |
| Documentation | ✅ | ✅ | ✅ Weekly | ✅ |
| AI Agents | ❌ | ❌ | ✅ Weekly | ✅ |
| Organization | ✅ | ❌ | ✅ Weekly | ✅ |
| Marketplace | ✅ | ✅ | ✅ Daily | ✅ |

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [GitHub Marketplace](https://github.com/marketplace?type=actions)
- [Dependabot Configuration](https://docs.github.com/en/code-security/dependabot)
- [CodeQL Documentation](https://codeql.github.com/docs/)
- [CrewAI Documentation](https://docs.crewai.com/)

## Maintenance

This guide was last updated: 2025-01-23

For questions or suggestions, please open an issue or discussion.
