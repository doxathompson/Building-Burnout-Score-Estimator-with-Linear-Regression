# Burnout Score Estimator - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- New stress level assessment questions (#45)
- Dark mode UI toggle (#52)
- Migration guide for v1.2 database changes

### Changed
- Mobile responsiveness improvements (#48)
- Session timeout increased to 60 minutes

### Security
- Patched CVE-2023-1234 in email dependency

### Migration Notes
To upgrade from v1.1 to v1.2:
```bash
python migrate_db.py --version 1.2