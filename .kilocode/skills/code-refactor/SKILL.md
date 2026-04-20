---
name: code-refactor
description: >
  Universal refactoring skill for database and code changes. Use this skill whenever:
  - User mentions renaming tables, columns, functions, classes, or variables
  - User mentions refactoring, migrating, or updating references
  - User mentions cleaning up obsolete code or old tables
  - User mentions fixing broken references after changes
  - User notices column/field name mismatches
  - User has duplicate tables or data structures
  - Any code or database restructuring task
---

# Universal Refactoring Skill

This skill handles ANY refactoring task with proper migration, verification, and cleanup.

## Phase 1: Discovery (Always Start Here)

### 1.1 Find All References
```bash
# For database names
grep -rn "old_table_name\|old_column" --include="*.py" .

# For code names  
grep -rn "old_function\|old_class\|old_variable" --include="*.py" .
```

### 1.2 Analyze Current State
```python
# Database analysis
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
cursor.execute("PRAGMA table_info(table_name)")

# Check column names from queries
cursor.execute("PRAGMA table_info(table_name)")
columns = [r[1] for r in cursor.fetchall()]  # names only
```

### 1.3 Check for Duplicates
```python
# Find duplicate tables
cursor.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE '%old%' OR name LIKE '%new%'
""")

# Find tables with similar names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
# Manually compare similar names
```

## Phase 2: Rename/Migration Pattern

### 2.1 Database Rename with Data Migration
```python
# Step 1: Check if both exist
# Step 2: Copy data BEFORE any deletion
cursor.execute("""
    INSERT INTO new_table (col1, col2, col3)
    SELECT col1, col2, col3 FROM old_table
    WHERE 1=1
""")
# Step 3: Verify row counts match
# Step 4: Update code references
# Step 5: Delete old table
```

### 2.2 Column Rename
```python
# Always use new column name in code
# Check dict(row) keys match expected names
# Common error: query returns "alias_name" but code expects "column"
```

### 2.3 Code Rename
```python
# Find all usages first
grep -rn "old_name" --include="*.py" .
# Update all occurrences
# Verify with grep again
```

## Phase 3: Column Name Alignment (Critical)

### 3.1 The dict(row) Problem
SQLite with column access returns keys from the SELECT clause, not table schema:
```python
# Query with alias
cursor.execute("SELECT si as starting_inventory FROM ...")
row = cursor.fetchone()
row["starting_inventory"]  # Works - use alias
row["si"]                   # Does NOT work - key is "starting_inventory"
```

### 3.2 Always Verify Keys
```python
row = cursor.fetchone()
print(row.keys())  # Always check exact key names
for key in row.keys():
    print(f"  {key}: {row[key]}")
```

### 3.3 Common Mismatches
- SQL: `SUM(col) as total` → Code expects `row["total"]`, not `row["col"]`
- SQL: `c.nom as categorie` → Code expects `row["categorie"]`
- SQL: `MAX(val)` → Code expects `row["MAX(val)"]` without alias

## Phase 4: Verification Checklist

### 4.1 Pre-Change Verification
- [ ] All references identified
- [ ] Backup/snapshot created
- [ ] Data integrity confirmed

### 4.2 Post-Change Verification
- [ ] Application starts without errors
- [ ] Data displays in UI correctly
- [ ] Calculations produce expected values
- [ ] No orphaned references (grep verifies)
- [ ] Insert/Update operations work

### 4.3 Code Verification
```bash
# Verify no old references remain
grep -rn "old_table\|old_column\|old_function" --include="*.py" .
```

## Phase 5: Cleanup

### 5.1 Safe Delete Order
1. Verify new structure works (step 4.2)
2. Delete old code/table (verify first!)
3. Clean up any backups

### 5.2 Never Delete Without Verification
- Always keep backup until fully verified
- Use DROP TABLE IF EXISTS for safety
- Add migration comments in code

## Common Refactoring Patterns

### Pattern A: Table Rename
```
1. CREATE new_table (if needed)
2. COPY data from old_table
3. UPDATE all Python references (grep)
4. VERIFY application works
5. DELETE old_table
```

### Pattern B: Column Rename
```
1. Check query returns correct alias
2. Update dict(row) access in code
3. Verify calculations work
```

### Pattern C: Function Rename
```
1. Find all call sites (grep)
2. Update all references
3. Update type hints
4. Verify no breaking changes
```

### Pattern D: Add Calculation
```
1. Identify formula
2. Find all insertion points
3. Calculate for each row
4. Update display/UI
5. Verify results make sense
```

## Output Requirements

When completing ANY refactoring task, provide:

1. **Summary**: "Renamed X to Y" or "Added calculation Z"
2. **Files Modified**: List all changed files
3. **Verification**: Commands to verify it worked
4. **Testing**: What to test in the UI
5. **Rollback**: How to undo if needed