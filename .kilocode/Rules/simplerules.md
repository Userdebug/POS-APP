# GLOBAL RULES

## 1. ENVIRONMENT & ISOLATION (VENV)
- **STRICT VENV:** All executions, installations, and tests must occur **EXCLUSIVELY** within the project's Virtual Environment.
- **CONTEXT AWARENESS:** Always read and integrate `AGENT.md` into the context before any action to ensure alignment with project history and goals.

## 2. MODULARITY & ATOMIZATION
- **SINGLE RESPONSIBILITY:** One file = one logical function or class. Prioritize reusable modules over monolithic scripts.
- **INTERNAL STRUCTURE:** Group by role within files (Imports > Constants > Types > Logic) using clear delimiters.
- **DECOUPLING:** Favor dependency injection to ensure every module is independently testable within the VENV.

## 3. FILE LIFECYCLE & ANTI-DUPLICATION
- **REFAC OVER CREATION:** Check existing files before creating new ones. Update or replace existing logic; **NEVER** duplicate functionality.
- **CLEAN SWEEP:** Explicitly delete obsolete files or temporary scripts once the new version is validated. 
- **NAMING CONVENTION:** Use functional names only. Suffixes like `_v1`, `_final`, or `_new` are **STRICTLY PROHIBITED**.

## 4. DEFINITION OF DONE (COMPLETION)
A task is only considered complete when:
- All code is executed, tested, and validated.
- Files are moved to their designated `/completed` or production folders.
- Logs are finalized and obsolete artifacts are deleted.
- Final status is documented using agent-specific skills (No handover without state persistence).