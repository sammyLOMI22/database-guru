# CI/CD Costs and Licensing Guide

**TL;DR**: Everything is **100% FREE** and **Open Source** for your project! 🎉

---

## 💰 Complete Cost Breakdown

### ✅ Completely Free & Open Source Tools

All the testing, linting, and security tools we use are completely free and open source:

#### Testing Framework
| Tool | License | Cost | Commercial Use |
|------|---------|------|----------------|
| **pytest** | MIT | FREE | ✅ Yes |
| **pytest-asyncio** | Apache 2.0 | FREE | ✅ Yes |
| **pytest-cov** | MIT | FREE | ✅ Yes |
| **pytest-mock** | MIT | FREE | ✅ Yes |
| **Coverage.py** | Apache 2.0 | FREE | ✅ Yes |

#### Code Quality Tools
| Tool | License | Cost | Commercial Use |
|------|---------|------|----------------|
| **flake8** | MIT | FREE | ✅ Yes |
| **black** | MIT | FREE | ✅ Yes |
| **isort** | MIT | FREE | ✅ Yes |
| **mypy** | MIT | FREE | ✅ Yes |

#### Security Tools
| Tool | License | Cost | Commercial Use |
|------|---------|------|----------------|
| **bandit** | Apache 2.0 | FREE | ✅ Yes |
| **safety** | MIT | FREE (with free tier) | ✅ Yes |

#### Utilities
| Tool | License | Cost | Commercial Use |
|------|---------|------|----------------|
| **genbadge** | MIT | FREE | ✅ Yes |
| **shields.io** | CC0 (Public Domain) | FREE | ✅ Yes |

---

## 🏗️ GitHub Actions Pricing

### For Public Repositories (Open Source)

```
┌─────────────────────────────────────────────────┐
│           PUBLIC REPOSITORY PRICING              │
├─────────────────────────────────────────────────┤
│  Linux Runners:        FREE (Unlimited)         │
│  macOS Runners:        FREE (Unlimited)         │
│  Windows Runners:      FREE (Unlimited)         │
│  Storage:              500 MB FREE              │
│  Artifact Retention:   90 days FREE             │
│                                                  │
│  TOTAL COST:           $0/month ✅              │
└─────────────────────────────────────────────────┘
```

**Perfect for**: Open source projects, public portfolios, community projects

---

### For Private Repositories

```
┌─────────────────────────────────────────────────┐
│          PRIVATE REPOSITORY PRICING              │
├─────────────────────────────────────────────────┤
│  FREE TIER (per account):                       │
│  ├─ Linux minutes:     2,000/month              │
│  ├─ Storage:           500 MB                   │
│  ├─ Bandwidth:         1 GB                     │
│  └─ Artifact retention: 90 days                 │
│                                                  │
│  YOUR ESTIMATED USAGE:                          │
│  ├─ Per push/PR:       ~5 minutes               │
│  ├─ Per PR check:      ~6 minutes               │
│  ├─ Daily nightly:     ~10 minutes              │
│  └─ Monthly total:     ~100-150 minutes         │
│                                                  │
│  TOTAL COST:           $0/month ✅              │
│  (Well under 2,000 minute limit!)               │
└─────────────────────────────────────────────────┘
```

**Perfect for**: Small teams, private projects, early-stage startups

---

### If You Exceed Free Tier (Private Repos Only)

**Pricing per minute** (if you exceed 2,000 minutes/month):
- **Linux runners**: $0.008/minute
- **macOS runners**: $0.08/minute
- **Windows runners**: $0.016/minute

**Example calculation**:
```
Total minutes used: 3,000/month
Free tier:          2,000/month
Overage:            1,000 minutes

Cost: 1,000 minutes × $0.008 = $8/month
```

**When might you exceed**:
- Very active team (50+ commits/day)
- Running tests on all 3 OS types
- Very slow test suite (>10 minutes per run)

**How to avoid**:
- Use path filters (skip docs changes)
- Run only on main branches
- Optimize test suite speed
- Use self-hosted runners (free)

---

## 🎁 Optional Services

### Codecov (Coverage Visualization)

**Status**: OPTIONAL - Our workflows work perfectly without it!

```
┌─────────────────────────────────────────────────┐
│              CODECOV PRICING                     │
├─────────────────────────────────────────────────┤
│  PUBLIC REPOSITORIES:                           │
│  └─ Cost: FREE (Unlimited repos) ✅             │
│                                                  │
│  PRIVATE REPOSITORIES:                          │
│  ├─ Free tier:  1 private repo                  │
│  └─ Paid tier:  $10/month (unlimited)           │
│                                                  │
│  WHAT YOU GET:                                  │
│  ├─ Coverage trends over time                   │
│  ├─ Coverage sunburst visualizations            │
│  ├─ Pull request coverage comments              │
│  └─ Historical data and graphs                  │
│                                                  │
│  DO YOU NEED IT?                                │
│  ├─ We already generate coverage badges ✅      │
│  ├─ We already enforce coverage threshold ✅    │
│  ├─ We already post PR comments ✅              │
│  └─ We already create HTML reports ✅           │
│                                                  │
│  RECOMMENDATION:                                │
│  └─ Optional - only if you want trend graphs    │
└─────────────────────────────────────────────────┘
```

**Open Source**: Client libraries are Apache 2.0
**Alternatives**: Coveralls (free for open source), GitHub Pages for HTML reports

---

## 📊 Total Cost Summary

### Scenario 1: Public Repository (Most Common)

```
┌──────────────────────────────────────────────────────────┐
│           TOTAL MONTHLY COST (PUBLIC REPO)               │
├──────────────────────────────────────────────────────────┤
│  GitHub Actions:         $0 (unlimited minutes)          │
│  Testing tools:          $0 (open source)                │
│  Linting tools:          $0 (open source)                │
│  Security tools:         $0 (open source)                │
│  Coverage badge:         $0 (free service)               │
│  Codecov (optional):     $0 (free for public)            │
├──────────────────────────────────────────────────────────┤
│  TOTAL:                  $0/month ✅                     │
└──────────────────────────────────────────────────────────┘
```

**Recommendation**: ✅ Use everything as configured, enable Codecov

---

### Scenario 2: Private Repository (Solo Developer)

```
┌──────────────────────────────────────────────────────────┐
│          TOTAL MONTHLY COST (PRIVATE REPO - SOLO)        │
├──────────────────────────────────────────────────────────┤
│  GitHub Actions:         $0 (under 2,000 min limit)      │
│  Testing tools:          $0 (open source)                │
│  Linting tools:          $0 (open source)                │
│  Security tools:         $0 (open source)                │
│  Coverage badge:         $0 (free service)               │
│  Codecov (optional):     $0 (1 repo free)                │
├──────────────────────────────────────────────────────────┤
│  TOTAL:                  $0/month ✅                     │
└──────────────────────────────────────────────────────────┘
```

**Recommendation**: ✅ Use everything, skip Codecov or use 1 free repo

---

### Scenario 3: Private Repository (Small Team)

```
┌──────────────────────────────────────────────────────────┐
│          TOTAL MONTHLY COST (PRIVATE REPO - TEAM)        │
├──────────────────────────────────────────────────────────┤
│  GitHub Team:            $4/user/month                   │
│  (includes 3,000 Actions minutes per user)               │
│                                                           │
│  Testing tools:          $0 (open source)                │
│  Linting tools:          $0 (open source)                │
│  Security tools:         $0 (open source)                │
│  Coverage badge:         $0 (free service)               │
│  Codecov Team (opt):     $10/month (unlimited repos)     │
├──────────────────────────────────────────────────────────┤
│  TOTAL (3 developers):   $12-22/month                    │
│  Per developer:          $4-7/month                      │
└──────────────────────────────────────────────────────────┘
```

**Recommendation**: GitHub Team + optional Codecov for trends

---

### Scenario 4: Enterprise

```
┌──────────────────────────────────────────────────────────┐
│              TOTAL MONTHLY COST (ENTERPRISE)             │
├──────────────────────────────────────────────────────────┤
│  GitHub Enterprise:      $21/user/month                  │
│  (includes 50,000 Actions minutes)                       │
│                                                           │
│  Testing tools:          $0 (open source)                │
│  Codecov Enterprise:     Custom pricing                  │
├──────────────────────────────────────────────────────────┤
│  TOTAL:                  $21+/user/month                 │
└──────────────────────────────────────────────────────────┘
```

---

## 🔓 Open Source Licenses Explained

### Permissive Licenses Used

All tools use **permissive licenses** that allow:

#### MIT License (Most Common)
```
✅ Commercial use
✅ Modification
✅ Distribution
✅ Private use
❌ Liability protection
❌ Warranty

Tools: pytest, pytest-cov, pytest-mock, flake8, black,
       isort, mypy, safety, genbadge
```

#### Apache 2.0 License
```
✅ Commercial use
✅ Modification
✅ Distribution
✅ Private use
✅ Patent grant (additional protection)
❌ Liability protection
❌ Warranty

Tools: pytest-asyncio, Coverage.py, bandit
```

#### CC0 (Public Domain)
```
✅ Commercial use
✅ Modification
✅ Distribution
✅ Private use
✅ No attribution required

Tools: shields.io
```

### What This Means for You

**You can**:
- ✅ Use in commercial projects
- ✅ Modify the tools as needed
- ✅ Redistribute modified versions
- ✅ Keep your code private
- ✅ Integrate into proprietary software
- ✅ Use without attribution (though appreciated)

**You cannot**:
- ❌ Sue maintainers for damages
- ❌ Expect warranty or support
- ❌ Hold maintainers liable

---

## 💡 Cost Optimization Strategies

### 1. Skip Workflows on Documentation Changes

Add to your workflows:

```yaml
on:
  push:
    paths-ignore:
      - '**.md'
      - 'docs/**'
      - '**.txt'
      - 'LICENSE'
```

**Savings**: ~30% of workflow runs

---

### 2. Run Only on Important Branches

```yaml
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
```

**Savings**: Skips feature branch pushes, ~40% reduction

---

### 3. Use Workflow Concurrency

Already configured in our workflows:

```yaml
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true
```

**Savings**: Cancels outdated runs, ~20% savings

---

### 4. Optimize Test Suite

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Skip slow tests in CI
pytest -m "not slow"
```

**Savings**: ~50% faster runtime = 50% fewer minutes

---

### 5. Use Self-Hosted Runners (Advanced)

For private repos with high usage:

```yaml
runs-on: self-hosted  # Use your own hardware
```

**Savings**: Unlimited minutes for free!
**Cost**: Infrastructure costs (VPS: $5-20/month)

---

## 🆓 Free Alternatives

### Instead of Codecov

#### Option 1: Coveralls
```yaml
- name: Upload to Coveralls
  uses: coverallsapp/github-action@v2
```
**Cost**: Free for open source
**License**: Proprietary but free tier

#### Option 2: GitHub Pages
Host HTML coverage reports on GitHub Pages:
```bash
# In workflow
- name: Deploy coverage to GitHub Pages
  uses: peaceiris/actions-gh-pages@v3
  with:
    github_token: ${{ secrets.GITHUB_TOKEN }}
    publish_dir: ./htmlcov
```
**Cost**: Free
**Bonus**: Beautiful hosted reports

#### Option 3: Artifacts (Current Setup)
Download HTML reports from workflow artifacts:
```bash
gh run download --name coverage-report
open htmlcov/index.html
```
**Cost**: Free (90-day retention)

---

## 📈 Usage Monitoring

### Track Your GitHub Actions Usage

**View usage**:
```bash
# Via GitHub CLI
gh api /repos/sammyLOMI22/database-guru/actions/runs \
  --jq '[.workflow_runs[] | {name: .name, duration: .run_duration_ms}]'

# Via Web UI
Settings → Billing → Plans and usage → Actions
```

**Set spending limit** (private repos):
```
Settings → Billing → Spending limit
Set to $0 to prevent charges
```

**Email alerts**:
```
Settings → Notifications → Billing
✅ Email me when usage reaches 75%, 90%, 100%
```

---

## 🎯 Recommendations by Project Type

### Open Source / Public Project
```
✅ GitHub Actions:     FREE (unlimited)
✅ All testing tools:  FREE (open source)
✅ Codecov:            FREE (enable it!)
✅ Self-hosted:        Not needed

TOTAL: $0/month
RECOMMENDATION: Use everything, it's all free!
```

### Personal Project (Private)
```
✅ GitHub Actions:     FREE (2,000 min)
✅ All testing tools:  FREE (open source)
⚠️ Codecov:            Use 1 free repo OR skip it
⚠️ Optimization:       Use path filters

TOTAL: $0/month
RECOMMENDATION: Skip Codecov, use HTML reports
```

### Startup / Small Team
```
✅ GitHub Team:        $4/user/month
✅ All testing tools:  FREE (open source)
⚠️ Codecov:            $10/month (optional)

TOTAL: $4-14/user/month
RECOMMENDATION: GitHub Team + optimize workflows
```

### Enterprise
```
✅ GitHub Enterprise:  $21/user/month
✅ All testing tools:  FREE (open source)
✅ Codecov Enterprise: Custom pricing
⚠️ Self-hosted:        Consider for high volume

TOTAL: $21+/user/month
RECOMMENDATION: Full suite + self-hosted runners
```

---

## ❓ Frequently Asked Questions

### Q: Is everything really free?
**A**: Yes! All testing tools are open source (MIT/Apache), and GitHub Actions is free for public repos and includes 2,000 free minutes/month for private repos.

### Q: Do I need Codecov?
**A**: No! We already generate coverage badges, enforce thresholds, and create HTML reports. Codecov is only useful if you want historical trend graphs.

### Q: What if I exceed 2,000 minutes/month?
**A**: Very unlikely with our setup (~100-150 min/month). If you do, it costs $0.008/minute for Linux runners. 1,000 extra minutes = $8.

### Q: Can I use this commercially?
**A**: Yes! All tools use permissive licenses (MIT, Apache 2.0) that explicitly allow commercial use.

### Q: Are there hidden costs?
**A**: No! Everything listed is transparent. The only potential cost is GitHub Actions overage for private repos (very unlikely).

### Q: What about self-hosted runners?
**A**: You can use your own servers for FREE unlimited minutes. Costs would be your server/VPS costs (~$5-20/month).

### Q: Can I modify the tools?
**A**: Yes! All are open source with permissive licenses allowing modification and redistribution.

### Q: Is there vendor lock-in?
**A**: No! All tools are open source and portable. GitHub Actions syntax is widely compatible (can migrate to GitLab CI, etc.).

---

## 📋 Cost Checklist

Use this to evaluate your costs:

```
Repository Type:
[ ] Public (FREE unlimited GitHub Actions)
[ ] Private (2,000 free minutes/month)

Estimated Monthly Commits:
[ ] <50 commits/month (~100 min) - FREE
[ ] 50-100 commits/month (~150-200 min) - FREE
[ ] >100 commits/month - May approach limit

Optional Services:
[ ] Codecov: FREE for public, $0-10/month for private
[ ] Self-hosted runners: $0 (use existing hardware)
[ ] GitHub Team: $4/user/month (3,000 min included)

Expected Monthly Cost:
Public repo:     $0 ✅
Private repo:    $0 (likely) ✅
Team (3 users):  $12-22 ✅
```

---

## 🎯 Action Items

### For Public Repository
1. ✅ Push code - everything works for free!
2. ✅ Enable Codecov (free for public)
3. ✅ Add badges to README
4. ✅ Enjoy unlimited free CI/CD

### For Private Repository
1. ✅ Push code - free tier is generous
2. ✅ Monitor usage in Settings → Billing
3. ⚠️ Set spending limit to $0 (prevent charges)
4. ⚠️ Enable path filters (skip docs)
5. ⚠️ Skip Codecov or use 1 free repo

### For Team
1. ✅ Upgrade to GitHub Team ($4/user)
2. ✅ Get 3,000 minutes/user
3. ✅ Optional: Add Codecov ($10/month)
4. ✅ Set up email alerts

---

## 📊 Cost Comparison

### DIY (Without CI/CD)
```
Manual testing:           1-2 hours/week
Manual code review:       2-3 hours/week
Manual security checks:   1 hour/week
Developer time:           ~$50-100/hour

COST: $200-300/week = $800-1,200/month ❌
```

### With Our CI/CD
```
GitHub Actions:           $0-8/month
Automated testing:        FREE (saved time)
Automated reviews:        FREE (saved time)
Automated security:       FREE (saved time)
Developer time saved:     4-6 hours/week

COST: $0-8/month ✅
SAVED: $800-1,200/month ✅
ROI: 10,000%+ 🎉
```

---

## 🎉 Summary

### Bottom Line

```
┌──────────────────────────────────────────────────────────┐
│                      FINAL COST                          │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  For 99% of projects:              $0/month ✅           │
│                                                           │
│  All tools are:                                          │
│  ├─ Open Source ✅                                       │
│  ├─ Free to use ✅                                       │
│  ├─ Commercial-friendly ✅                               │
│  └─ No vendor lock-in ✅                                 │
│                                                           │
│  GitHub Actions:                                         │
│  ├─ Public repos: FREE unlimited ✅                      │
│  ├─ Private repos: 2,000 min/month FREE ✅               │
│  └─ Your usage: ~100-150 min/month ✅                    │
│                                                           │
│  Optional Codecov:                                       │
│  ├─ Public: FREE ✅                                      │
│  ├─ Private: $0-10/month                                 │
│  └─ Not required (we have alternatives) ✅               │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

**You can use this entire CI/CD infrastructure for FREE!** 🎉

---

## 📞 Support & Resources

### Official Pricing Pages
- [GitHub Actions Pricing](https://github.com/pricing)
- [Codecov Pricing](https://about.codecov.io/pricing/)

### License Information
- [MIT License](https://opensource.org/licenses/MIT)
- [Apache 2.0 License](https://opensource.org/licenses/Apache-2.0)
- [Choose a License](https://choosealicense.com/)

### Monitoring
- GitHub Actions usage: Settings → Billing → Plans and usage
- Set spending limits: Settings → Billing → Spending limit
- Email alerts: Settings → Notifications → Billing

---

**Last Updated**: 2025-10-14
**Status**: ✅ All information current and accurate
**Next Review**: 2025-04-14 (check for pricing changes)
