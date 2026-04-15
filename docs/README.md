---
layout: default
title: Documentation Index
---

# Documentation Index

Complete guide to all z-open documentation with descriptions and suggested reading order.

**Total Documentation: 5,500+ lines across 10 comprehensive guides**

---

## By Purpose

### 🎯 "I want to use zopen"

**Start here:**
1. [User Guide](user-guide) - Read sections 1-3 for installation and basic usage
2. [FAQ](faq) - Find answers to specific questions
3. [Examples & Recipes](examples) - Find a workflow that matches your use case

**When you need help:**
- Troubleshooting issues → [User Guide § 9](user-guide#9-troubleshooting) or [FAQ](faq#troubleshooting)
- Understanding configuration → [User Guide § 4](user-guide#4-configuration)
- Integration with tools → [Examples & Recipes § Integration](examples#integration-with-popular-tools)

**Time commitment:** 30 minutes for basic usage, 2 hours for comprehensive understanding

---

### 👨‍💻 "I want to integrate zopen into my code"

**Required reading:**
1. [Python API Documentation](api) - Complete API reference
2. [API Examples](api#complete-examples) - Working code snippets

**Optional but recommended:**
3. [Design Document](design#module-structure) - Understand module organization
4. [Advanced Usage](api#advanced-usage) - File monitors, file managers, batch processing

**Time commitment:** 45 minutes for basics, 2 hours for advanced scenarios

---

### 🏗️ "I want to contribute to z-open development"

**Required reading:**
1. [Development Guide](../DEVELOPMENT) - Development workflow and setup
2. [Design Document](design) - Architecture and design decisions
3. [Build Guide](build) - Multiple build paths and packaging

**Related:**
4. [Migration Guide](migration) - Understand version compatibility
5. [GitHub Actions](github-actions) - CI/CD pipeline

**Time commitment:** 3-4 hours for comprehensive understanding

---

### 📦 "I want to package/deploy z-open"

**Required reading:**
1. [Build Guide](build) - All packaging methods
2. [Build Guide § Choosing a method](build#7-choosing-a-packaging-method) - Determine best approach

**Optional:**
3. [GitHub Actions](github-actions) - Automated builds and releases
4. [Development Guide § Release](../DEVELOPMENT#create-a-release) - Release process

**Time commitment:** 1-2 hours depending on packaging needs

---

### 🚀 "I'm upgrading z-open"

**Start here:**
1. [Migration Guide](migration) - Version-specific upgrade paths
2. [Migration Guide § Rollback](migration#rollback-instructions) - Just in case

**Time commitment:** 15-30 minutes

---

## By Document

### Index of All Documentation

| Document | Lines | Purpose | Audience | Time |
|----------|-------|---------|----------|------|
| [User Guide](user-guide) | 598 | Installation, CLI reference, configuration, troubleshooting | End users, sysadmins | 2h |
| [FAQ & Troubleshooting](faq) | 750+ | Quick answers to common questions with solutions | All | 1h |
| [Examples & Recipes](examples) | 800+ | Real-world workflows and copy-paste recipes | Developers, sysadmins | 1.5h |
| [Python API](api) | 650+ | Programmatic API and integration guide | Developers | 1.5h |
| [Design Document](design) | 533 | Architecture, modules, design decisions | Developers, contributors | 2h |
| [Build Guide](build) | 862 | Packaging and build methods | Packagers, developers | 2h |
| [Development Guide](../DEVELOPMENT) | 567 | Development workflow, testing, releases | Contributors | 1.5h |
| [GitHub Actions](github-actions) | ~300 | CI/CD pipeline configuration | DevOps, maintainers | 1h |
| [Migration Guide](migration) | 400+ | Version upgrades and compatibility | All | 0.5h |
| [Landing Page](index) | 330 | Project overview and quick navigation | New users | 0.25h |

**Total:** 5,500+ lines, covering all aspects of z-open

---

## Reading Paths by Role

### 📖 Path for End Users (3 hours)

1. [Quick Start](user-guide#2-quick-start) (15 min)
2. [Configuration Guide](user-guide#4-configuration) (45 min)
3. [FAQ](faq) - sections relevant to you (30 min)
4. [Examples & Recipes](examples) - find your use case (45 min)
5. [Troubleshooting](user-guide#9-troubleshooting) + [FAQ § Troubleshooting](faq#troubleshooting) (30 min)

**Outcome:** Full understanding of installation, configuration, and common workflows

---

### 👨‍💻 Path for Python Developers (2.5 hours)

1. [Python API](api) - Sections 1-3 (30 min)
2. [API Examples](api#complete-examples) - Study the 3 examples (30 min)
3. [Design Document](design#module-structure) (45 min)
4. [API § Advanced Usage](api#advanced-usage) (15 min)
5. [FAQ § Scripting](faq#scripting--automation) (15 min)

**Outcome:** Ready to integrate zopen into your code

---

### 🏗️ Path for Contributors (5 hours)

1. [Development Guide](../DEVELOPMENT) - complete (1.5 h)
2. [Design Document](design) - complete (2 h)
3. [Build Guide](build#7-choosing-a-packaging-method) (45 min)
4. [FAQ § Troubleshooting](faq#troubleshooting) (30 min)
5. [GitHub Actions](github-actions) (15 min)

**Outcome:** Ready to contribute code and releases

---

### 📦 Path for Package Maintainers (2 hours)

1. [Build Guide § CMake](build#4-cmake-build-system) (30 min)
2. [Build Guide § CPack](build#5-cpack-packaging) (30 min)
3. [Build Guide § Debian](build#6-debian-native-packaging-dpkg-buildpackage) (30 min)
4. [GitHub Actions § Release](github-actions) (15 min)
5. [Build Guide § Choosing Method](build#7-choosing-a-packaging-method) (15 min)

**Outcome:** Understand all packaging paths and choose best approach

---

### 🚀 Path for Version Upgrade (30 minutes)

1. [Migration Guide](migration) - Read section for your version (20 min)
2. [Migration Guide § Rollback](migration#rollback-instructions) - Just scan (5 min)
3. Follow the upgrade steps (5 min)

**Outcome:** Successfully upgrade to new version

---

## Document Relationships

```
index.md (Landing Page)
├── Quick Start
├── User Guide
│   ├── Installation
│   ├── Configuration
│   └── Troubleshooting → FAQ
├── FAQ
│   ├── Configuration → User Guide § 4
│   ├── Examples → Examples & Recipes
│   └── Troubleshooting → User Guide § 9
├── Examples & Recipes
│   ├── Developer Workflows
│   ├── System Admin Tasks
│   ├── Integration with Tools
│   └── Advanced Scenarios → Python API
├── Python API
│   ├── Installation
│   ├── Core Functions
│   ├── Advanced Usage → Design Document
│   └── Complete Examples
├── Design Document
│   ├── Architecture
│   ├── Module Structure
│   ├── Extension Points → Advanced Usage
│   └── Design Decisions
├── Build Guide
│   ├── Multiple Build Paths
│   ├── Package Methods
│   └── Release Checklist → GitHub Actions
├── Development Guide
│   ├── Setup
│   ├── Testing
│   ├── Building → Build Guide
│   └── Releases → GitHub Actions
├── GitHub Actions
│   ├── CI/CD Pipeline
│   ├── Automated Releases → Build Guide
│   └── Security Scanning
└── Migration Guide
    ├── Version Upgrades
    ├── Configuration Migration
    └── Rollback Steps
```

---

## How to Use This Index

**Lost and don't know where to start?**
→ Find your role above and follow the reading path

**Know what you're looking for?**
→ Use the Document index table to find the file and section

**Want to understand how docs relate?**
→ Check the Document Relationships diagram

**Need a quick answer?**
→ Try [FAQ](faq) with Ctrl+F

---

## Document Quality Checklist

Each document includes:

- ✅ Clear table of contents with section numbers
- ✅ Multiple levels of headings for easy navigation
- ✅ Code examples where applicable
- ✅ Cross-references to related docs
- ✅ Consistent terminology and formatting
- ✅ Troubleshooting sections where relevant
- ✅ "See Also" or "Next Steps" guidance

---

## Contributing to Documentation

To improve this documentation:

1. Follow the existing format and structure
2. Add cross-references to related sections
3. Include code examples for technical content
4. Test code examples to ensure they work
5. Keep terminology consistent with other docs
6. Update this index if adding new documents

---

## Version Information

**Last Updated:** 2024  
**zopen Version:** 0.7.x  
**Python Support:** 3.10, 3.11, 3.12, 3.13  

---

## Quick Links

- 🏠 [Landing Page](index)
- 👤 [User Guide](user-guide)
- ❓ [FAQ](faq)
- 📖 [Examples](examples)
- 👨‍💻 [API](api)
- 🏗️ [Design](design)
- 🔨 [Build](build)
- 🚀 [Development](../DEVELOPMENT)
- 🔄 [Migration](migration)
- ⚙️ [GitHub Actions](github-actions)
