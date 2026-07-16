# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project follows [Semantic Versioning](https://semver.org/).

## Unreleased

### Planned

- Runtime controller integration with an explicit read-only mode
- Additional Clash rule types and rule-provider inspection

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
