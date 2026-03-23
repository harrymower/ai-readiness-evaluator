# Scripts Directory

This directory contains utility scripts for the AI Readiness Evaluator project.

## audit_apis.py

**Purpose:** Audit all APIs in `config/apis.txt` and generate a complexity signals report.

**Usage:**
```bash
python scripts/audit_apis.py
```

**Output:** `docs/phase0_api_signals.md`

**What it does:**
1. Loads API test scenarios from `config/apis.txt`
2. Loads service-level metadata from `config/api_metadata.yaml`
3. Matches each test scenario to its parent API service
4. Collects 6 complexity signals per API:
   - Auth required (Y/N/Optional)
   - Pagination supported (Y/N)
   - Total endpoints count
   - Schema depth (shallow/medium/deep)
   - Average response size (KB)
   - Error surface (low/medium/high)
5. Generates a markdown report with summary statistics and detailed table

**Requirements:**
- PyYAML (`pip install pyyaml`)

**Related Files:**
- Input: `config/apis.txt` - API test scenarios
- Input: `config/api_metadata.yaml` - Service-level complexity metadata
- Output: `docs/phase0_api_signals.md` - Generated report

