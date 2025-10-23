# Workflows Quick Start Guide

Get up and running with the automated workflows in 5 minutes!

## 🚀 Immediate Benefits

Once you merge this PR, you'll automatically get:

✅ **Code quality checks** on every push  
✅ **Security scanning** for vulnerabilities and secrets  
✅ **Automated dependency updates** via Dependabot  
✅ **File header management** for documentation  
✅ **Code formatting** enforcement  
✅ **AI-powered analysis** (with API keys)  

## 📋 Initial Setup (5 minutes)

### Step 1: Merge This PR ✨

1. Review the changes in this PR
2. Merge to main branch
3. Workflows will automatically activate

### Step 2: Configure Secrets (Optional but Recommended)

Navigate to: **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

#### Essential Secrets (for AI features):
```
OPENROUTER_API_KEY=your_key_here
# OR
LOCALAI_BASE_URL=http://your-local-ai-endpoint
```

#### Optional Secrets (for enhanced features):
```
CODECOV_TOKEN=your_codecov_token
SNYK_TOKEN=your_snyk_token
SONAR_TOKEN=your_sonarcloud_token
GITGUARDIAN_API_KEY=your_gitguardian_key
```

**Don't have these?** No problem! Most workflows work without them, just with reduced functionality.

### Step 3: Verify Workflows

1. Go to the **Actions** tab
2. You should see workflows running
3. Check that they complete successfully

## 🎯 Quick Wins

### 1. Run Your First AI Agent (2 minutes)

1. Go to **Actions** tab
2. Select "🤖 CrewAI Advanced AI Agents"
3. Click **Run workflow**
4. Select an agent (try `code-review-agent`)
5. Click **Run workflow** button
6. Wait 2-5 minutes
7. Check the artifact downloads for the report

### 2. Fix File Headers (Automatic)

The file header workflow will automatically:
- Detect files without headers
- Add standardized headers
- Create a PR for review

**Next time you push code**, check for the automated PR!

### 3. Update Dependencies (Automatic)

Dependabot will automatically:
- Check for dependency updates weekly
- Create PRs for each update
- Group by package ecosystem

**Check your PRs** in a few days!

### 4. Review Security Findings

1. Go to **Security** tab
2. Click **Code scanning alerts**
3. Review any findings
4. Many are auto-detected from CodeQL

## 💡 Developer Workflow

### Before You Commit

Run these locally to match CI checks:

```bash
# Format Python code
black .
isort .

# Format JavaScript/TypeScript
npx prettier --write .

# Lint Python
flake8 .

# Lint JavaScript/TypeScript
npx eslint .

# Run tests
npm test
```

### When You Create a PR

Workflows automatically run:
- ✅ Code quality checks
- ✅ Security scans
- ✅ Test execution
- ✅ Dependency reviews
- ✅ Format checks

**Check the PR status** to see all results!

### Review AI Suggestions

After workflows complete:
1. Check PR comments for AI feedback
2. Download artifacts for detailed reports
3. Apply suggestions as appropriate

## 🛠️ Customization

### Adjust Workflow Triggers

Edit workflow files in `.github/workflows/` to change when they run:

```yaml
# Run on specific branches
on:
  push:
    branches: [main, develop, feature/*]

# Run on specific paths
on:
  push:
    paths:
      - '**.py'
      - 'requirements.txt'

# Change schedule
on:
  schedule:
    - cron: '0 2 * * 1'  # Weekly on Monday at 2 AM
```

### Configure Dependabot

Edit `.github/dependabot.yml`:

```yaml
# Change update frequency
schedule:
  interval: "daily"  # or "weekly" or "monthly"

# Change PR limits
open-pull-requests-limit: 5
```

### Customize Linting Rules

Edit configuration files:
- `.eslintrc.json` - ESLint rules
- `.prettierrc.json` - Prettier settings
- `pyproject.toml` - Python tool settings

## 🔧 Common Tasks

### Run a Specific Workflow Manually

1. Go to **Actions** tab
2. Select the workflow from the left sidebar
3. Click **Run workflow** dropdown
4. Choose branch and options
5. Click **Run workflow** button

### View Workflow Results

1. **Actions** tab → Click on workflow run
2. Click on job name to see logs
3. Scroll to see step details
4. Download artifacts at the bottom

### Disable a Workflow Temporarily

1. **Actions** tab
2. Select workflow from left sidebar
3. Click **⋯** menu → **Disable workflow**
4. Re-enable when ready

### Debug Workflow Failures

1. Click failed workflow run
2. Click failed job
3. Expand failed step
4. Check error messages
5. Fix issue locally and push

## 📊 Monitoring

### Weekly Summary

Every week, check:
- [ ] Security tab for new alerts
- [ ] Dependabot PRs to review
- [ ] AI analysis reports (if scheduled)
- [ ] Code metrics trends

### Monthly Review

Once a month, review:
- [ ] Workflow efficiency (run times)
- [ ] Failed workflow patterns
- [ ] Documentation coverage
- [ ] Dependency health

## 🎓 Learning More

### Explore Individual Workflows

Each workflow file (`.github/workflows/*.yml`) is documented with:
- Purpose and features
- When it runs
- What it produces

### Read the Full Guide

See `.github/WORKFLOWS_GUIDE.md` for comprehensive documentation.

### GitHub Actions Docs

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Workflow Syntax](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions)

## 🆘 Getting Help

### Workflow Not Running?

1. Check workflow file syntax
2. Verify trigger conditions match your changes
3. Check if workflow is disabled
4. Review branch protection rules

### Job Failing?

1. Read error message in logs
2. Check if dependencies are installed
3. Verify required secrets are set
4. Test command locally

### Need Assistance?

1. Check existing issues
2. Review workflow logs thoroughly
3. Open an issue with:
   - Workflow name
   - Run link
   - Error message
   - What you expected

## ✅ Checklist

After setup, you should have:

- [x] PR merged to main
- [ ] Checked Actions tab shows workflows
- [ ] At least one workflow run completed
- [ ] (Optional) Added API keys for AI features
- [ ] (Optional) Configured code quality tool tokens
- [ ] Read the full WORKFLOWS_GUIDE.md
- [ ] Ran a manual workflow to test
- [ ] Checked Security tab configuration

## 🎉 You're All Set!

Your repository now has:
- 🤖 12 automated workflow files
- 🛡️ 6+ security scanning tools
- 📊 5+ code quality tools
- 📚 4+ documentation generators
- 🔄 Automatic dependency updates
- 🎨 Automatic code formatting
- 📝 Automatic file headers
- 🧠 AI-powered analysis

Sit back and let automation improve your code quality! 🚀

## 📅 Next Steps

1. **Week 1:** Monitor workflow runs, fix any issues
2. **Week 2:** Review Dependabot PRs, merge safe updates
3. **Week 3:** Try manual AI agent workflows
4. **Week 4:** Customize workflows for your needs
5. **Ongoing:** Maintain and improve automation

---

**Questions?** Open an issue or check the full guide in `.github/WORKFLOWS_GUIDE.md`
