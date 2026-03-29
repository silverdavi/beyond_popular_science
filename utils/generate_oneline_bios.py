#!/usr/bin/env python3
"""
Generate one-line biographies:
Name, years (or era), nationality, one-line bio, Nobel symbol if applicable, chapters
"""

import csv
import re
from pathlib import Path

# Chapter number to label mapping (must match main.tex)
CHAPTER_LABELS = {
    '01': 'ch:goldrelativity',
    '02': 'ch:acceleratinguniverse',
    '03': 'ch:banach',
    '04': 'ch:energytransmission',
    '05': 'ch:circlewheel',
    '06': 'ch:gravitytimedilation',
    '07': 'ch:billiardsconicsporism',
    '08': 'ch:boundedprimegaps',
    '09': 'ch:arrowtheoremtopology',
    '10': 'ch:solarfusionquantumtunneling',
    '11': 'ch:topologicalinsulators',
    '12': 'ch:gsmencryptionorder',
    '13': 'ch:poissonsspot',
    '14': 'ch:compacttwinparadox',
    '15': 'ch:envelopeparadox',
    '16': 'ch:falsevacuumthreat',
    '17': 'ch:bignumbers',
    '18': 'ch:speculativeexecutionattacks',
    '19': 'ch:cosmicraymuons',
    '20': 'ch:chineseroomargument',
    '21': 'ch:exponentialmapslietheory',
    '22': 'ch:minecraftcreeper',
    '23': 'ch:blackholetimedilationredshift',
    '24': 'ch:4dspacetime',
    '25': 'ch:fireflybioluminescence',
    '26': 'ch:jewishcalendar',
    '27': 'ch:planetaryskycolors',
    '28': 'ch:negativetemperature',
    '29': 'ch:hatmonotile',
    '30': 'ch:simpsonsparadox',
    '31': 'ch:osmosisdebye',
    '32': 'ch:atomic',
    '33': 'ch:incubationinequality',
    '34': 'ch:boltzmannbrain',
    '35': 'ch:treesfromair',
    '36': 'ch:qftvsgr',
    '37': 'ch:darkmatterevidence',
    '38': 'ch:christmastruce1914',
    '39': 'ch:superpermutationsbreakthrough',
    '40': 'ch:dnasequencing',
    '41': 'ch:hough',
    '42': 'ch:iceslipperiness',
    '43': 'ch:nearflatuniverse',
    '44': 'ch:ironmask',
    '45': 'ch:maxwelldemon',
    '46': 'ch:woodwardhoffmannrules',
    '47': 'ch:observervac',
    '48': 'ch:threebody',
    '49': 'ch:ivfmtdna',
    '50': 'ch:consciousness',
}

def parse_chapters(chapter_str):
    """Parse chapter string."""
    if not chapter_str:
        return []
    chapters = [ch.strip() for ch in chapter_str.split('|')]
    normalized = set()
    for ch in chapters:
        match = re.match(r'(\d+)', ch)
        if match:
            num = int(match.group(1))
            normalized.add(f"{num:02d}")
    return sorted(list(normalized))

def format_years(birth, death):
    """Format years or era for display."""
    unknown_vals = ['unknown', 'N/A', 'N/A (Fictional)', '', 
                    'c. 14th–13th Century BCE (Traditional dating)']
    
    # Special case: Fictional characters
    if birth == 'Fictional' or death == 'Fictional':
        return "Fictional"
    
    birth_unknown = birth in unknown_vals or not birth
    death_unknown = death in unknown_vals or not death
    
    # If both unknown, try to extract era from birth/death fields
    if birth_unknown and death_unknown:
        # Check if there's any era information
        if birth and 'BCE' in birth:
            return birth
        elif birth and 'century' in birth.lower():
            return birth
        return ""
    
    # If birth has full dates
    if 'BCE' in birth or 'BC' in birth or 'century' in birth.lower():
        return f"{birth}–{death}" if not death_unknown else birth
    
    # If only death unknown but birth known
    if not birth_unknown and death_unknown:
        return f"b. {birth}"
    
    # If death is "living"
    if death and 'living' in death.lower():
        return f"b. {birth}"
    
    # Both known
    return f"{birth}–{death}"

NOBEL_SYMBOLS = {
    'Physics':   '\\nobelphysics',
    'Chemistry': '\\nobelchemistry',
    'Medicine':  '\\nobelmedicine',
    'Economics': '\\nobeleconomics',
    'Literature':'\\nobelliterature',
}

def get_nobel_prefix(data):
    """Return discipline-specific Nobel symbol to place before the name, or empty string."""
    year = data.get('nobel_prize_year', '')
    if not year or str(year).strip() in ['', 'nan']:
        return ""
    category = data.get('nobel_prize_category', '').strip()
    return NOBEL_SYMBOLS.get(category, '\\nobelphysics') + ' '

def sanitize_filename(name):
    """Create safe filename."""
    safe = re.sub(r'[^\w\s-]', '', name.lower())
    safe = re.sub(r'[-\s]+', '_', safe)
    return safe

def fix_latex_accents(text):
    """Fix LaTeX accent commands by adding braces where needed."""
    # Common LaTeX accent commands that need braces: \", \', \^, \`, \~, \=, \., \u, \v, \H, \c
    # Pattern: backslash + accent char + letter (without braces) -> add braces
    # Example: \"o -> \"{o}, \'e -> \'{e}
    accent_pattern = r'\\(["\'^`~=.uvHc])([a-zA-Z])'
    fixed = re.sub(accent_pattern, r'\\\1{\2}', text)
    return fixed

def convert_to_smart_quotes(text):
    """Convert straight quotes to smart curly quotes."""
    # Define smart quote characters (paste actual Unicode characters here)
    OPEN_QUOTE = '“'   # U+201C LEFT DOUBLE QUOTATION MARK - PASTE HERE
    CLOSE_QUOTE = '”'  # U+201D RIGHT DOUBLE QUOTATION MARK - PASTE HERE
    OPEN_QUOTE = '"'   # U+201C LEFT DOUBLE QUOTATION MARK - PASTE HERE
    CLOSE_QUOTE = '"'  # U+201D RIGHT DOUBLE QUOTATION MARK - PASTE HERE
    
    STRAIGHT_QUOTE = '"'  # U+0022 QUOTATION MARK
    
    # Simple state-based replacement: alternate between opening and closing
    result = []
    in_quote = False
    
    for i, char in enumerate(text):
        if char == '"':
            # Skip if this is part of a LaTeX command (preceded by backslash)
            if i > 0 and text[i-1] == '\\':
                result.append(char)  # Keep as straight quote for LaTeX commands
            elif not in_quote:
                result.append(OPEN_QUOTE)
                in_quote = True
            else:
                result.append(CLOSE_QUOTE)
                in_quote = False
        else:
            result.append(char)
    
    return ''.join(result)

def generate_oneline_file(name, data, output_dir, used_filenames):
    """Generate one-line biography file."""
    base_filename = sanitize_filename(name)
    filename = base_filename
    counter = 2
    
    while filename in used_filenames:
        filename = f"{base_filename}_{counter}"
        counter += 1
    
    used_filenames.add(filename)
    filepath = output_dir / f"{filename}.tex"
    
    years = format_years(data['birth_year'], data['death_year'])
    chapters = parse_chapters(data['Chapters'])
    # Create hyperlinked chapter references
    chapter_links = []
    for ch in chapters:
        if ch in CHAPTER_LABELS:
            chapter_links.append(f"\\hyperref[{CHAPTER_LABELS[ch]}]{{{ch}}}")
        else:
            chapter_links.append(ch)
    chapters_display = ", ".join(chapter_links)
    nobel_prefix = get_nobel_prefix(data)
    
    # Get one-line bio from CSV
    one_line = data.get('bio_one_sentence', '').strip()
    if not one_line or len(one_line) < 20:
        # Fallback: use first sentence of biography_latex or biography
        bio_text = data.get('biography_latex', data.get('biography', ''))
        # Extract first sentence
        sentences = re.split(r'[.!?]\s+', bio_text)
        one_line = sentences[0] if sentences else "Biography not available."
        if len(one_line) > 200:
            one_line = one_line[:197] + "..."
    
    # Remove ONLY surrounding straight double quotes (from CSV formatting)
    # Don't touch LaTeX quotes like `` or ''
    if one_line.startswith('"') and one_line.endswith('"'):
        one_line = one_line[1:-1].strip()
    
    # Fix LaTeX accent commands
    one_line = fix_latex_accents(one_line)
    
    # Convert straight quotes in NAME to LaTeX quotes
    # "Word" → ``Word''
    # Replace pairs of straight quotes
    import re as re_inner
    name = re_inner.sub(r'"([^"]+)"', r"``\1''", name)  # "text" → ``text''
    
    # Convert to smart quotes
    name = convert_to_smart_quotes(name)
    one_line = convert_to_smart_quotes(one_line)
    
    content = f"""% One-line biography: {name}
{nobel_prefix}\\textbf{{{name}}}"""
    
    if years:
        content += f" ({years})"
    
    content += f". {one_line}"
    
    if chapters:
        content += f" \\emph{{[Ch.~{chapters_display}]}}"
    
    content += "\n\n"
    
    filepath.write_text(content, encoding='utf-8')
    return filename

def get_last_name(name):
    """Extract last name for sorting, ignoring parenthetical content."""
    # Remove parenthetical content for sorting
    cleaned = re.sub(r'\([^)]*\)', '', name).strip()
    parts = cleaned.split()
    return parts[-1] if parts else name

def generate_oneline_loader(person_dict, output_file, filenames, nobel_count):
    """Generate loader for one-line bios (used in test file)."""
    sorted_names = sorted(person_dict.keys(), key=get_last_name)
    sorted_filenames = [filenames[name] for name in sorted_names]
    
    content = r"""%
% Compact reference for all people mentioned in the book

\chapter*{Biographical Index}
\addcontentsline{toc}{chapter}{Biographical Index}

\small
\setlength{\parskip}{0.5em}

"""
    content += (
        "\\noindent\\textit{Nobel Prize laureates are marked before their name: "
        "\\nobelphysics Physics, \\nobelchemistry Chemistry, "
        "\\nobelmedicine Physiology or Medicine, \\nobeleconomics Economics, "
        "and \\nobelliterature Literature.}\n"
    )
    
    for filename in sorted_filenames:
        content += f"\\input{{oneline_bios/{filename}.tex}}\n"
    
    output_file.write_text(content, encoding='utf-8')

def generate_oneline_bios_content(person_dict, output_file, filenames, nobel_count):
    """
    Generate the root-level `oneline_bios_content.tex` that the main book includes.
    This mirrors `oneline_loader.tex` but uses the `people/oneline_bios/` path
    and adds a visible explanation for the Nobel symbol.
    """
    sorted_names = sorted(person_dict.keys(), key=get_last_name)
    sorted_filenames = [filenames[name] for name in sorted_names]

    # Header comments (not printed)
    content = "%\n One-Line Biographies\n% Compact reference for all people mentioned in the book\n\n"

    content += (
        "\\noindent\\textit{Nobel Prize laureates are marked before their name: "
        "\\nobelphysics Physics, \\nobelchemistry Chemistry, "
        "\\nobelmedicine Physiology or Medicine, \\nobeleconomics Economics, "
        "and \\nobelliterature Literature.}\n\n"
    )

    for filename in sorted_filenames:
        content += f"\\input{{people/oneline_bios/{filename}.tex}}\n"

    output_file.write_text(content, encoding='utf-8')

def main():
    print("Generating one-line biography system...")
    print("=" * 80)
    
    base_dir = Path(__file__).resolve().parent.parent
    people_dir = base_dir / 'people'
    # Use the cleaned CSV with only essential columns
    csv_path = people_dir / 'people_BIOGRAPHIES.csv'
    
    # Create output directory
    oneline_dir = people_dir / 'oneline_bios'
    oneline_dir.mkdir(exist_ok=True)
    
    # Load CSV
    print(f"\n[1/3] Loading CSV: {csv_path}")
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"   Total people: {len(rows)}")
    
    # Count Nobel laureates once so we can use it in all generated files
    nobel_count = sum(
        1
        for row in rows
        if row.get('nobel_prize_year')
        and str(row['nobel_prize_year']).strip()
        and str(row['nobel_prize_year']) not in ['', 'nan']
    )
    
    # Generate one-line files
    print(f"\n[2/3] Generating one-line biography files...")
    person_dict = {}
    filenames = {}
    used_filenames = set()
    
    for row in rows:
        name = row['Person'].strip()
        if name:
            filename = generate_oneline_file(name, row, oneline_dir, used_filenames)
            filenames[name] = filename
            person_dict[name] = row
    
    print(f"   [ok] Generated {len(filenames)} one-line files")
    
    # Generate loader
    print(f"\n[3/3] Generating loader...")
    loader_file = people_dir / 'oneline_loader.tex'
    generate_oneline_loader(person_dict, loader_file, filenames, nobel_count)
    print(f"   [ok] Loader saved to: {loader_file.name}")

    # Generate root-level oneline_bios_content.tex for the main book
    content_file = base_dir / 'oneline_bios_content.tex'
    generate_oneline_bios_content(person_dict, content_file, filenames, nobel_count)
    print(f"   [ok] oneline_bios_content.tex updated with {len(filenames)} entries")
    
    print(f"\n" + "=" * 80)
    print(f"[ok] COMPLETE!")
    print(f"=" * 80)
    print(f"\nGenerated:")
    print(f"  [dir] oneline_bios/        - {len(filenames)} one-line files")
    print(f"  [file] oneline_loader.tex   - Loader file")
    print(f"\nStatistics:")
    print(f"  Total people: {len(person_dict)}")
    print(f"  Nobel laureates: {nobel_count} (Nobel)")
    print(f"\nFormat:")
    print(f"  Name (years) --- Nationality. One-line bio. (Nobel) [Ch. XX, YY]")

if __name__ == '__main__':
    main()

