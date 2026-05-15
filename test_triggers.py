import sqlite3

DB_PATH = "college0.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn

print("=" * 55)
print("TESTING TRIGGERS")
print("=" * 55)

# ── TEST 1: Enrollment insert trigger ─────────────────────
print("\n--- Test 1: Enrollment insert trigger ---")
conn = get_conn()
cursor = conn.cursor()

# Clean up any leftover row from a previous test run
# so this test is safe to run multiple times
cursor.execute("""
    DELETE FROM enrollments
    WHERE student_id = 15 AND section_id = 6
""")
conn.commit()

# Also reset the section count to match reality after cleanup
cursor.execute("""
    UPDATE class_sections
    SET current_enrollment = (
        SELECT COUNT(*) FROM enrollments
        WHERE section_id = 6 AND status = 'enrolled'
    )
    WHERE section_id = 6
""")
conn.commit()

cursor.execute("""
    SELECT current_enrollment, status
    FROM class_sections WHERE section_id = 6
""")
before = cursor.fetchone()
print(f"Before: enrollment={before['current_enrollment']} status={before['status']}")

# Insert a new enrollment — trigger should increment the count
cursor.execute("""
    INSERT INTO enrollments (student_id, section_id, status)
    VALUES (15, 6, 'enrolled')
""")
conn.commit()

cursor.execute("""
    SELECT current_enrollment, status
    FROM class_sections WHERE section_id = 6
""")
after = cursor.fetchone()
print(f"After:  enrollment={after['current_enrollment']} status={after['status']}")
print("✓ PASS" if after['current_enrollment'] == before['current_enrollment'] + 1
      else "✗ FAIL — count did not increment")

# ── TEST 2: Drop enrollment trigger ───────────────────────
print("\n--- Test 2: Drop enrollment trigger ---")
cursor.execute("""
    UPDATE enrollments SET status = 'dropped'
    WHERE student_id = 15 AND section_id = 6
""")
conn.commit()

cursor.execute("""
    SELECT current_enrollment FROM class_sections WHERE section_id = 6
""")
dropped = cursor.fetchone()
print(f"After drop: enrollment={dropped['current_enrollment']}")
print("✓ PASS" if dropped['current_enrollment'] == before['current_enrollment']
      else "✗ FAIL — count did not decrement")

conn.close()

# ── TEST 3: Warning insert trigger ────────────────────────
print("\n--- Test 3: Warning insert trigger ---")
conn = get_conn()
cursor = conn.cursor()

# Clean up any test warning from a previous run first
cursor.execute("""
    DELETE FROM warning_records
    WHERE user_id = 10
      AND reason = 'Test warning from trigger test'
""")
conn.commit()

cursor.execute("SELECT warning_count FROM users WHERE user_id = 10")
before_warn = cursor.fetchone()['warning_count']
print(f"Before: warning_count={before_warn}")

cursor.execute("""
    INSERT INTO warning_records (user_id, reason, source_module, active_flag)
    VALUES (10, 'Test warning from trigger test', 'academic', 1)
""")
conn.commit()

cursor.execute("SELECT warning_count FROM users WHERE user_id = 10")
after_warn = cursor.fetchone()['warning_count']
print(f"After:  warning_count={after_warn}")
print("✓ PASS" if after_warn == before_warn + 1
      else "✗ FAIL — warning_count did not increment")

# ── TEST 4: Warning deactivate trigger ────────────────────
print("\n--- Test 4: Warning deactivate trigger ---")
cursor.execute("""
    UPDATE warning_records
    SET active_flag = 0
    WHERE user_id = 10
      AND reason = 'Test warning from trigger test'
""")
conn.commit()

cursor.execute("SELECT warning_count FROM users WHERE user_id = 10")
deact_warn = cursor.fetchone()['warning_count']
print(f"After deactivate: warning_count={deact_warn}")
print("✓ PASS" if deact_warn == before_warn
      else "✗ FAIL — warning_count did not decrement")

conn.close()

# ── TEST 5: Cannot review after grade posted ──────────────
print("\n--- Test 5: Review blocked after grade posted ---")
conn = get_conn()
cursor = conn.cursor()

# enrollment_id=1 (Alice in SEC-001) already has a grade (A)
# so Alice should NOT be able to review SEC-001
try:
    cursor.execute("""
        INSERT INTO reviews
            (section_id, student_id, rating,
             original_text, display_text, visibility_status)
        VALUES (1, 7, 5, 'Great course!', 'Great course!', 'published')
    """)
    conn.commit()
    print("✗ FAIL — should have been blocked by trigger")
except sqlite3.IntegrityError as e:
    print(f"✓ PASS — trigger blocked it: {e}")

conn.close()

print("\n" + "=" * 55)
print("All trigger tests complete.")
print("=" * 55)