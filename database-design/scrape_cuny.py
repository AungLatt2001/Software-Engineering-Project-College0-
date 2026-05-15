# ============================================================
# College0 — CUNY Global Search Parser
# File: scrape_cuny.py
#
# Parses the saved CUNY Global Search HTML files.
# Works with both the Results pages and Details pages.
#
# Run: python3 scrape_cuny.py
# ============================================================

from bs4 import BeautifulSoup
import json
import re
import os
import glob

OUTPUT_FILE = "cuny_sections.json"

# Parse ALL html files in the project folder that match cuny_*
HTML_FILES = sorted(glob.glob("cuny_*.html"))


def to_24h(t):
    """
    Convert '2:00PM' → '14:00'
    Convert '10:00AM' → '10:00'
    """
    t = t.strip().upper().replace(' ', '')
    if not t or len(t) < 5:
        return 'TBA'
    ampm = t[-2:]
    time_part = t[:-2]
    try:
        hour, minute = time_part.split(':')
        hour = int(hour)
        if ampm == 'PM' and hour != 12:
            hour += 12
        if ampm == 'AM' and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute}"
    except Exception:
        return 'TBA'


def parse_days_times(raw):
    """
    Parses 'TuTh 2:00PM-3:15PM' or 'MoWe 4:00PM-5:40PM'
    into a list of timeslot dicts.

    Handles multiple time blocks on separate lines like:
        MoWe 4:00PM-5:40PM
        Fr 2:00PM-3:40PM

    Returns list of:
        {'day': 'Tuesday', 'start': '14:00', 'end': '15:15'}
    """
    day_map = [
        ('Mo', 'Monday'),
        ('Tu', 'Tuesday'),
        ('We', 'Wednesday'),
        ('Th', 'Thursday'),
        ('Fr', 'Friday'),
        ('Sa', 'Saturday'),
        ('Su', 'Sunday'),
    ]

    results = []
    # Split on newlines — each line is one time block
    lines = [l.strip() for l in re.split(r'[\n\r]+', raw)
             if l.strip()]

    for line in lines:
        # Match: "TuTh 2:00PM-3:15PM" or "MoWe 4:00PM - 5:40PM"
        m = re.match(
            r'^([A-Za-z]+)\s+'
            r'(\d{1,2}:\d{2}[AaPp][Mm])'
            r'\s*[-–]\s*'
            r'(\d{1,2}:\d{2}[AaPp][Mm])',
            line
        )
        if not m:
            continue

        day_str   = m.group(1)
        start_24  = to_24h(m.group(2))
        end_24    = to_24h(m.group(3))

        # Parse the day abbreviations
        remaining = day_str
        while remaining:
            matched = False
            for abbr, full in day_map:
                if remaining.startswith(abbr):
                    results.append({
                        'day':   full,
                        'start': start_24,
                        'end':   end_24,
                    })
                    remaining = remaining[len(abbr):]
                    matched = True
                    break
            if not matched:
                remaining = remaining[1:]

    return results


def parse_results_page(soup, filename):
    """
    Parses a Results page (Global Class Search 1/2 - Results.html).
    These pages have a summary table with columns:
    CLASS | SECTION | DAYS & TIMES | ROOM | INSTRUCTOR |
    INSTRUCTION MODE | MEETING DATES | STATUS | COURSE TOPIC
    """
    sections = []
    current_code  = None
    current_title = None

    # Find course headers — they look like:
    # "CSC 10400 - Discrete Structrs 1"
    # They appear as links or text nodes before each table

    # Strategy: walk through all elements in order
    body = soup.find('body')
    if not body:
        return sections

    all_elements = body.find_all(['a', 'div', 'p', 'span',
                                   'h1', 'h2', 'h3', 'h4',
                                   'table', 'td', 'li'])

    i = 0
    while i < len(all_elements):
        el = all_elements[i]

        # Check if this element contains a course code
        text = el.get_text(strip=True)
        course_match = re.match(
            r'(CSC\s+\d{4,6})\s*[-–]\s*(.+)', text
        )
        if course_match and len(text) < 80:
            current_code  = course_match.group(1).strip()
            current_title = course_match.group(2).strip()
            # Clean trailing numbers/codes
            current_title = re.sub(
                r'\s*\d+\s*$', '', current_title
            ).strip()

        # Check if this is a results table
        if el.name == 'table':
            header_cells = el.find_all('th')
            header_text  = ' '.join(
                th.get_text(strip=True).upper()
                for th in header_cells
            )

            if 'CLASS' in header_text and 'DAYS' in header_text:
                # This is a section results table
                rows = el.find_all('tr')[1:]  # skip header

                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue

                    cell_texts = [
                        c.get_text(separator='\n', strip=True)
                        for c in cells
                    ]

                    # Map columns by header position
                    headers = [
                        th.get_text(strip=True).upper()
                        for th in el.find_all('th')
                    ]

                    def get_col(keyword):
                        for idx, h in enumerate(headers):
                            if keyword in h and idx < len(cell_texts):
                                return cell_texts[idx]
                        return ''

                    class_num  = get_col('CLASS')
                    days_raw   = get_col('DAYS')
                    room       = get_col('ROOM')
                    instructor = get_col('INSTRUCTOR')
                    status_raw = get_col('STATUS')

                    # Skip rows with no schedule
                    if not days_raw or 'TBA' in days_raw.upper():
                        i += 1
                        continue

                    timeslots = parse_days_times(days_raw)
                    if not timeslots:
                        i += 1
                        continue

                    # Unique days list preserving order
                    seen = set()
                    days = []
                    for t in timeslots:
                        if t['day'] not in seen:
                            days.append(t['day'])
                            seen.add(t['day'])

                    section = {
                        "course_code":   current_code or 'UNKNOWN',
                        "course_title":  current_title or '',
                        "class_number":  class_num.strip(),
                        "instructor":    instructor.strip() or 'TBA',
                        "days":          days,
                        "time_start":    timeslots[0]['start'],
                        "time_end":      timeslots[0]['end'],
                        "all_timeslots": timeslots,
                        "room":          room.strip() or 'TBA',
                        "capacity":      30,
                        "source_file":   filename,
                    }
                    sections.append(section)

        i += 1

    return sections


def parse_details_page(soup, filename):
    """
    Parses a Details page (Global Class Search 3 - Details.html).
    These pages have a single section's full information including
    the classinfo table with Days & Times, Room, Instructor.

    Also extracts: capacity, enrollment, course description.
    """
    sections = []

    # ── Get course code and title from the shadowbox ─────────
    shadowbox = soup.find(class_='shadowbox')
    code, title = 'UNKNOWN', ''
    if shadowbox:
        raw = shadowbox.get_text(separator='\n', strip=True)
        m = re.search(r'(CSC\s+\d{4,6})\s*[-–]\s*(.+)', raw)
        if m:
            code  = m.group(1).strip()
            title = m.group(2).strip()
            # Remove "City College | ..." trailing info
            title = title.split('\n')[0].strip()
            title = re.sub(r'\s*City College.*', '', title).strip()

    # ── Get capacity from Class Availability table ────────────
    capacity = 30
    cap_match = re.search(
        r'Class Capacity.*?(\d+)', soup.get_text(), re.DOTALL
    )
    if cap_match:
        capacity = int(cap_match.group(1))

    # ── Parse the classinfo meeting table ────────────────────
    # This is the table with class: "classinfo"
    # Columns: Days & Times | Room | Instructor | Meeting Dates
    meeting_table = soup.find('table', class_='classinfo')
    if not meeting_table:
        # Fallback: find table with "Days & Times" header
        for tbl in soup.find_all('table'):
            if 'Days' in tbl.get_text():
                meeting_table = tbl
                break

    if not meeting_table:
        return sections

    rows = meeting_table.find_all('tr')[1:]  # skip header

    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 3:
            continue

        days_raw   = cells[0].get_text(separator='\n', strip=True)
        room       = cells[1].get_text(strip=True)
        instructor = cells[2].get_text(strip=True)

        if not days_raw or 'TBA' in days_raw.upper():
            continue

        timeslots = parse_days_times(days_raw)
        if not timeslots:
            continue

        seen = set()
        days = []
        for t in timeslots:
            if t['day'] not in seen:
                days.append(t['day'])
                seen.add(t['day'])

        section = {
            "course_code":   code,
            "course_title":  title,
            "class_number":  '',
            "instructor":    instructor or 'TBA',
            "days":          days,
            "time_start":    timeslots[0]['start'],
            "time_end":      timeslots[0]['end'],
            "all_timeslots": timeslots,
            "room":          room or 'TBA',
            "capacity":      capacity,
            "source_file":   filename,
        }
        sections.append(section)

    return sections


def parse_file(filepath):
    """
    Auto-detects whether a file is a Results page or
    a Details page and calls the right parser.
    """
    filename = os.path.basename(filepath)
    print(f"  Parsing: {filename}")

    with open(filepath, 'r', encoding='utf-8',
              errors='replace') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')
    title_tag = soup.find('title')
    page_title = title_tag.get_text() if title_tag else ''

    if 'Details' in page_title or 'Details' in filename:
        results = parse_details_page(soup, filename)
    else:
        results = parse_results_page(soup, filename)

    print(f"  → {len(results)} sections found")
    return results


def deduplicate(sections):
    """
    Remove duplicate sections by class_number.
    If class_number is empty, deduplicate by
    course_code + days + time_start combination.
    """
    seen = set()
    unique = []
    for s in sections:
        key = s['class_number'] if s['class_number'] else \
              f"{s['course_code']}_{s['time_start']}_{''.join(s['days'])}"
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return unique


def main():
    print("=" * 55)
    print("CUNY Global Search — HTML File Parser")
    print("=" * 55)
    print()

    if not HTML_FILES:
        print("ERROR: No cuny_*.html files found in this folder.")
        print()
        print("Rename your saved HTML files to start with 'cuny_':")
        print("  cuny_results_1.html")
        print("  cuny_results_2.html")
        print("  cuny_details.html")
        return

    print(f"Found {len(HTML_FILES)} HTML file(s) to parse:")
    for f in HTML_FILES:
        print(f"  {f}")
    print()

    all_sections = []
    for filepath in HTML_FILES:
        sections = parse_file(filepath)
        all_sections.extend(sections)

    # Remove duplicates
    all_sections = deduplicate(all_sections)

    print()
    print(f"Total unique sections: {len(all_sections)}")

    if not all_sections:
        print()
        print("No sections were extracted.")
        print("Make sure you expanded all courses before saving.")
        return

    # Save to JSON
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(all_sections, f, indent=2)

    print(f"✓ Saved to {OUTPUT_FILE}")
    print()

    # Preview
    print("Preview — first 8 sections:")
    print("-" * 55)
    for s in all_sections[:8]:
        print(f"{s['course_code']}  {s['course_title']}")
        print(f"  Instructor : {s['instructor']}")
        print(f"  Days       : {', '.join(s['days'])}")
        print(f"  Time       : {s['time_start']} – {s['time_end']}")
        print(f"  Room       : {s['room']}")
        print(f"  Capacity   : {s['capacity']}")
        print()

    print("=" * 55)
    print("Next step: python3 seed_from_cuny.py")
    print("=" * 55)


if __name__ == "__main__":
    main()