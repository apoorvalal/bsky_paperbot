# Typst-Based Text Justification for Abstract Images

**Date**: 2026-01-01
**Status**: Approved
**Context**: Replace PIL manual justification with Typst professional typesetting

## Problem

The current PIL-based abstract image generation uses manual word spacing calculation for text justification, resulting in:
- Uneven word spacing creating "rivers" of whitespace
- No hyphenation support, forcing awkward line breaks
- Unprofessional appearance compared to proper typeset documents

## Solution Overview

Replace PIL text rendering with Typst-based typesetting pipeline while maintaining image dimensions and GitHub Actions compatibility.

## Architecture

### High-Level Flow
```
Paper data → Typst template → typst compile → PNG bytes → Bluesky upload
```

### Component Breakdown

1. **Typst Template** (`abstract_template.typ`)
   - Defines document structure (title, authors, abstract)
   - Configures professional typesetting rules
   - Single template populated with dynamic data

2. **Python Integration** (modified `create_abstract_image()`)
   - Check Typst availability via `shutil.which('typst')`
   - Populate template with paper data
   - Execute Typst CLI to generate PNG
   - Fall back to PIL if Typst unavailable

3. **GitHub Actions Setup**
   - Use `typst-community/setup-typst@v3` action
   - ~15MB binary download, cached between runs
   - Adds 5-10s to first workflow run, <1s on cached runs

## Implementation Details

### Typst Template Specifications

**Page Layout**:
- Width: 4 inches (600px at 150 DPI)
- Height: Auto (crop to content)
- Margins: 0.27 inches (40px) all sides

**Typography**:
- Title: 18pt bold serif, left-aligned, single-spaced
- Authors: 12pt italic serif, left-aligned
- Abstract header: 14pt bold serif
- Body text: 11pt serif, justified with hyphenation
- Line spacing: Single throughout

**Typst Features Leveraged**:
- Automatic hyphenation (no manual dictionary needed)
- Professional word spacing algorithm
- Proper kerning and line breaking
- No "rivers" in justified text

### Python Implementation

**File**: `paperbot.py:17` (`create_abstract_image()`)

**Logic Flow**:
```python
if shutil.which('typst'):
    # Typst path
    1. Populate template with title, authors, abstract
    2. Write to /tmp/abstract_{hash}.typ
    3. Run: typst compile --format png /tmp/abstract_{hash}.typ
    4. Read PNG bytes from /tmp/abstract_{hash}.png
    5. Cleanup temp files
    6. Return PNG bytes
else:
    # PIL fallback (existing implementation)
    [current PIL code remains unchanged]
```

**Error Handling**:
- Wrap Typst execution in try/except
- Log warning on fallback to PIL
- Ensure graceful degradation for local development

**Template Substitution**:
- Simple string replacement or f-string formatting
- Escape special Typst characters in user data (if needed)
- No heavyweight templating engine required

### GitHub Actions Integration

**Preferred Approach** (using official action):
```yaml
steps:
  - uses: actions/checkout@v4

  - name: Set up Typst
    uses: typst-community/setup-typst@v3

  - name: Set up Python
    uses: actions/setup-python@v4
    with:
      python-version: '3.x'

  - name: Install dependencies
    run: pip install -r requirements.txt

  - name: Run bot
    run: python paperbot.py
```

**Alternative Approach** (manual binary download):
```yaml
- name: Install Typst
  run: |
    wget https://github.com/typst/typst/releases/download/v0.12.0/typst-x86_64-unknown-linux-musl.tar.xz
    tar -xf typst-x86_64-unknown-linux-musl.tar.xz
    sudo mv typst-x86_64-unknown-linux-musl/typst /usr/local/bin/
```

**Performance Characteristics**:
- First run: ~15MB download + ~5-10s setup
- Cached runs: <1s setup overhead
- Typst rendering: ~0.5-1s per document
- Total impact: Negligible compared to network operations

## Trade-offs and Considerations

### Advantages
- Professional typesetting quality matching LaTeX/academic papers
- Automatic hyphenation with no manual dictionary management
- Proper justification algorithm eliminates spacing issues
- Fast rendering (~1s per document)
- Clean, maintainable template-based approach

### Disadvantages
- Adds ~15MB to GitHub Actions environment
- Additional dependency to maintain
- Slightly more complex setup than pure Python
- Requires subprocess execution

### Accepted Trade-offs
- 15MB binary acceptable for professional output quality
- Typst is stable and well-maintained (low maintenance burden)
- Fallback to PIL ensures robustness
- Setup complexity minimal with official GitHub Action

## Success Criteria

1. Abstract images show even word spacing in justified text
2. Long words hyphenate properly at line breaks
3. Overall appearance matches professional typeset documents
4. GitHub Actions workflow runs successfully with Typst
5. Local development works with or without Typst installed
6. No degradation in image dimensions or readability

## Future Enhancements

- Consider additional Typst features (columns, citations, etc.)
- Explore other output formats (SVG for scalability)
- Template variants for different paper types
- Batch rendering optimization if posting multiple papers

## References

- Typst documentation: https://typst.app/docs
- GitHub Action: https://github.com/typst-community/setup-typst
- Current implementation: `paperbot.py:17-127`
