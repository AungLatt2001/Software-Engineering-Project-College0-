# Copilot Instructions for College0 / CUNY0 Project

## Architecture Overview
This is a Python-based college database simulation using SQLite. The system models students, instructors, courses, enrollments, reviews, and academic standing. Key components:
- **Database Schema** (`schema.sql`): Defines tables with CHECK constraints (e.g., user roles must be 'student', 'instructor', or 'registrar'; ratings 1-5).
- **Data Layer** (`queries.py`): All database operations organized into 8 groups (authentication, registration, GPA, etc.). Each function follows: `get_connection()` → parameterized query → fetch results → close.
- **Initialization** (`initialize_db.py`, `seed_db.py`): Creates and populates the DB from `schema.sql` and `seed_data.sql`.
- **Testing** (`test_queries.py`): Validates query functions.

Data flows through SQLite with foreign key enforcement. Design emphasizes data integrity and specific academic rules (e.g., GPA thresholds for termination/warnings).

## Key Patterns
- **Query Pattern**: Use `get_connection()` for DB access with `PRAGMA foreign_keys = ON` and `row_factory = sqlite3.Row`. Always use `?` placeholders for parameters. Example:
  ```python
  conn = get_connection()
  cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
  user = cursor.fetchone()
  conn.close()
  return user
  ```
- **Result Handling**: Return dict-like objects (via Row factory) for easy access like `row['first_name']`.
- **Academic Logic**: GPA calculations exclude 'W'/'I' grades; standing reviews use CASE expressions for actions (TERMINATE if GPA < 2.0, WARNING if 2.0-2.25, HONOR_ROLL if >3.5).
- **Error Handling**: Catch `sqlite3.IntegrityError` for constraint violations (e.g., duplicate enrollments).

## Workflows
- **Setup Database**: Run `python initialize_db.py` to create schema, then `python seed_db.py` to insert data.
- **Run Tests**: Execute `python test_queries.py` to validate all query functions.
- **Debug Queries**: Add print statements in `queries.py`; use SQLite browser for DB inspection.
- **Add New Queries**: Follow the group structure in `queries.py`; ensure parameterized queries and proper connection handling.

## Integration Points
- **Dependencies**: Only standard `sqlite3` and `re` modules.
- **No External APIs**: Self-contained SQLite database.
- **Cross-Component**: Queries span multiple tables (e.g., `get_student_profile` joins users/students).

Reference: `queries.py` for all patterns; `schema.sql` for constraints.