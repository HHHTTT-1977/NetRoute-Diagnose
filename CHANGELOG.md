# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## Unreleased

### Planned

- Runtime controller integration with an explicit read-only mode
- Additional Clash rule types and rule-provider inspection

## 0.1.2 - 2026-08-21

### Added

- PyPI distribution support through the isolated GitHub Actions Trusted
  Publishing workflow

### Changed

- Document PyPI installation with `pip install netroute-diagnose` alongside
  the existing GitHub source-package and development installation methods

## 0.1.1 - 2026-08-10

### Added

- A macOS and Windows Python 3.12 smoke-test job, while retaining the full
  Linux Python 3.10, 3.11, and 3.12 test matrix
- A security policy and structured bug-report and feature-request templates
- A sanitized CLI visual demo alongside the existing HTML report preview

### Changed

- Clearer user-first installation and Quick Start guidance in Chinese and
  English
- Three common routing-diagnosis scenarios and a more prominent privacy/data
  flow explanation
- Package version and release metadata prepared for v0.1.1

## 0.1.0 - 2026-07-16

### Added

- Read-only DNS checks through the system resolver or an explicit DNS server
- Public egress IP checks for system, direct, and explicit HTTP proxy modes
- Static first-match analysis for common Clash/OpenClash domain rules
- App routing expectation checks with PASS, MISMATCH, UNCERTAIN, and UNKNOWN
- Built-in WeChat, Apple, Google, and OpenAI profiles
- Standalone HTML reports and optional JSON output
- Chinese and English documentation, synthetic examples, tests, and CI

### Security

- Reports retain configuration filenames without exposing absolute local paths
- Repository examples use loopback or documentation-only IP address ranges
