from queries import *

print("=" * 50)
print("TESTING ALL QUERIES")
print("=" * 50)

print("\n--- Q1: Login lookup ---")
user = get_user_by_email('a.chen@college0.edu')
print(f"Found: {user['first_name']} {user['last_name']} | Role: {user['role']}")

print("\n--- Q2: Top GPA students ---")
for s in get_top_gpa_students():
    print(f"  {s['first_name']} {s['last_name']}: {s['cumulative_gpa']}")

print("\n--- Q3: Highest rated sections ---")
for s in get_highest_rated_sections():
    print(f"  {s['course_code']}: {s['avg_rating']} stars ({s['review_count']} reviews)")

print("\n--- Q4: Available sections ---")
for s in get_available_sections(1):
    print(f"  {s['course_code']} | {s['seats_remaining']} seats | {s['status']}")

print("\n--- Q5: Enrollment count for Alice (id=7) ---")
count = get_student_enrollment_count(7, 1)
print(f"  Alice is enrolled in {count} courses")

print("\n--- Q6: Conflict check (Alice trying SEC-003) ---")
conflicts = check_schedule_conflict(7, 3)
if conflicts:
    for c in conflicts:
        print(f"  Conflict: {c['conflicting_course']} on {c['day_of_week']}")
else:
    print("  No conflict found")

print("\n--- Q7: Capacity check for SEC-003 ---")
cap = check_section_capacity(3)
print(f"  Enrolled: {cap['current_enrollment']}/{cap['capacity']} | Status: {cap['status']}")

print("\n--- Q8: GPA calculation for Alice (id=7) ---")
gpa = calculate_student_gpa(7)
print(f"  GPA: {gpa['cumulative_gpa']} from {gpa['courses_graded']} courses")

print("\n--- Q9: Academic standing review ---")
for s in get_students_needing_standing_review():
    print(f"  {s['full_name']}: GPA {s['cumulative_gpa']} → {s['standing_action']}")

print("\n--- Q10: Graduation check for Grace (id=13) ---")
g = check_graduation_eligibility(13)
print(f"  Eligible: {g['eligible']}")
print(f"  Completed: {g['total_completed']}/8 courses, {g['core_completed']}/4 core")
print(f"  GPA: {g['cumulative_gpa']}")

print("\n--- Q11: Taboo word scan ---")
text = "The pacing was terrible and the instructor was awful."
found = scan_for_taboo_words(text)
print(f"  Found {len(found)} taboo words: {found}")
masked = mask_taboo_words(text, found)
print(f"  Masked: {masked}")

print("\n--- Q12: Waitlist for SEC-003 ---")
wl = get_waitlist(3)
for entry in wl:
    print(f"  Position {entry['position']}: {entry['student_name']}")

print("\nAll tests complete.")