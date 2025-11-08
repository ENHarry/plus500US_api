# Post-Live-Test Cleanup Checklist

After successful live testing, the following files/directories can be safely removed:

## Directories to Remove After Live Test
- `scraped_data/` - Network capture data (once endpoints are verified)
- `screenshots/` - WebDriver debugging screenshots
- `session_backup/` - Session analysis data
- Any remaining `__pycache__/` directories
- `.pytest_cache/` directories

## Files to Remove After Live Test
- `endpoint_analysis_and_extraction.md` - API analysis documentation
- Any remaining `.log` files
- Any remaining `.json` test result files
- Development documentation files (`PHASE*.md`, `IMPLEMENTATION*.md`, etc.)

## Files to Keep for Production
- All files in `plus500us_client/` (core SDK code)
- All files in `tests/` (test suite)
- All files in `examples/` (user examples)
- All files in `docs/` (documentation)
- `README.md`, `LICENSE`, `pyproject.toml`, `requirements.txt`
- `.env.example`, `.gitignore`
- `.github/` (CI/CD configuration)

## Command for Final Cleanup
After live testing is successful, run:
```bash
python cleanup_artifacts.py --aggressive
```

This will perform the full cleanup while preserving only production-ready files.