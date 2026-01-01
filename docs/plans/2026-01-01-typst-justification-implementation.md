# Typst Text Justification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace PIL manual text justification with Typst professional typesetting for abstract images.

**Architecture:** Create Typst template for abstract layout, modify `create_abstract_image()` to use Typst CLI when available with PIL fallback, update GitHub Actions workflow to install Typst.

**Tech Stack:** Typst (typesetting), Python subprocess (execution), GitHub Actions (CI/CD)

---

## Task 1: Create Typst Template

**Files:**
- Create: `abstract_template.typ`

**Step 1: Create Typst template file**

Create `abstract_template.typ` in the repository root with the following content:

```typst
// Abstract image template for Bluesky bot
// Page setup - 4 inches wide, auto height
#set page(
  width: 4in,
  height: auto,
  margin: (x: 0.27in, y: 0.27in),
)

// Typography settings
#set text(
  font: "Linux Libertine",  // Default serif font, cross-platform
  size: 11pt,
  fallback: true,
)

// Paragraph settings - justified with hyphenation
#set par(
  justify: true,
  leading: 0.65em,  // Single spacing
)

// Title placeholder - will be replaced by Python
#text(size: 18pt, weight: "bold")[
  {{TITLE}}
]

#v(8pt)

// Authors placeholder - will be replaced by Python
#text(size: 12pt, style: "italic")[
  {{AUTHORS}}
]

#v(16pt)

// Abstract header
#text(size: 14pt, weight: "bold")[
  Abstract
]

#v(6pt)

// Abstract body placeholder - will be replaced by Python
#text(size: 11pt)[
  {{ABSTRACT}}
]
```

**Step 2: Verify template syntax**

Run: `typst compile abstract_template.typ --format png abstract_template.png` (if Typst is installed locally)

Expected: Either succeeds with placeholder text, or skip if Typst not installed locally (will test in GitHub Actions)

**Step 3: Commit template**

```bash
git add abstract_template.typ
git commit -m "feat: add Typst template for abstract images"
```

---

## Task 2: Modify Python Code to Use Typst

**Files:**
- Modify: `paperbot.py:17-127` (entire `create_abstract_image` method)

**Step 1: Add imports at top of file**

Add these imports after existing imports in `paperbot.py`:

```python
import shutil
import subprocess
import hashlib
import tempfile
import os
```

**Step 2: Create helper method for Typst rendering**

Add this new method to the `ArxivBot` class (insert before `create_abstract_image` method):

```python
def _render_with_typst(self, title: str, abstract: str, authors: str) -> bytes:
    """Render abstract image using Typst. Returns PNG bytes or raises exception."""
    # Read template
    template_path = os.path.join(os.path.dirname(__file__), 'abstract_template.typ')
    with open(template_path, 'r') as f:
        template = f.read()

    # Escape special Typst characters in user data
    def escape_typst(text: str) -> str:
        # Escape backslashes first, then special chars
        text = text.replace('\\', '\\\\')
        text = text.replace('#', '\\#')
        text = text.replace('[', '\\[')
        text = text.replace(']', '\\]')
        text = text.replace('{', '\\{')
        text = text.replace('}', '\\}')
        return text

    # Populate template
    content = template.replace('{{TITLE}}', escape_typst(title))
    content = content.replace('{{AUTHORS}}', escape_typst(authors))
    content = content.replace('{{ABSTRACT}}', escape_typst(abstract))

    # Create temp files with unique names
    content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
    temp_dir = tempfile.gettempdir()
    typ_path = os.path.join(temp_dir, f'abstract_{content_hash}.typ')
    png_path = os.path.join(temp_dir, f'abstract_{content_hash}.png')

    try:
        # Write populated template
        with open(typ_path, 'w') as f:
            f.write(content)

        # Compile with Typst
        result = subprocess.run(
            ['typst', 'compile', typ_path, png_path, '--format', 'png'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            raise Exception(f"Typst compilation failed: {result.stderr}")

        # Read PNG bytes
        with open(png_path, 'rb') as f:
            return f.read()

    finally:
        # Cleanup temp files
        for path in [typ_path, png_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass  # Ignore cleanup errors
```

**Step 3: Modify create_abstract_image to use Typst with fallback**

Replace the beginning of `create_abstract_image` method (keep existing PIL code as fallback). Change lines 17-19 to:

```python
def create_abstract_image(self, title: str, abstract: str, authors: str) -> bytes:
    """Generate a formatted PNG image of the paper abstract"""

    # Try Typst first if available
    if shutil.which('typst'):
        try:
            return self._render_with_typst(title, abstract, authors)
        except Exception as e:
            # Log warning and fall back to PIL
            print(f"Warning: Typst rendering failed ({e}), falling back to PIL")

    # PIL fallback (existing implementation below)
```

Keep all existing PIL code (lines 19-127) unchanged below this addition.

**Step 4: Commit Python changes**

```bash
git add paperbot.py
git commit -m "feat: add Typst rendering with PIL fallback"
```

---

## Task 3: Update GitHub Actions Workflow

**Files:**
- Modify: `.github/workflows/post.yml:10-22`

**Step 1: Add Typst setup step**

Modify `.github/workflows/post.yml` to add Typst installation after checkout and before Python setup:

```yaml
    steps:
      - name: Checkout Repository
        uses: actions/checkout@v3
        with:
          repository: ${{ github.event.pull_request.head.repo.full_name }}
          ref: ${{ github.event.pull_request.head.ref }}

      - name: Set up Typst
        uses: typst-community/setup-typst@v3

      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
          cache: 'pip' # caching pip dependencies
      - run: pip install -r requirements.txt
      - name: scrape and run
        run: python3 paperbot.py
        env:
          BSKYBOT: ${{ secrets.BSKYBOT }}
          BSKYPWD: ${{ secrets.BSKYPWD }}
      - name: Commit and push
        uses: EndBug/add-and-commit@v9
        with:
          add: "."
          push: true
          default_author: github_actions
```

**Step 2: Commit workflow changes**

```bash
git add .github/workflows/post.yml
git commit -m "feat: add Typst to GitHub Actions workflow"
```

---

## Task 4: Test Locally (Optional - Skip if Typst Not Installed)

**Files:**
- Test: `paperbot.py`

**Step 1: Install Typst locally (macOS)**

Only if you want to test locally:

```bash
brew install typst
```

**Step 2: Create test script**

Create `test_typst.py` with:

```python
from paperbot import ArxivBot
import os

# Create test instance (will fail on client.login but we don't need that)
class TestBot:
    def _render_with_typst(self, title, abstract, authors):
        # Copy method from ArxivBot
        import shutil
        import subprocess
        import hashlib
        import tempfile

        template_path = 'abstract_template.typ'
        with open(template_path, 'r') as f:
            template = f.read()

        def escape_typst(text):
            text = text.replace('\\', '\\\\')
            text = text.replace('#', '\\#')
            text = text.replace('[', '\\[')
            text = text.replace(']', '\\]')
            text = text.replace('{', '\\{')
            text = text.replace('}', '\\}')
            return text

        content = template.replace('{{TITLE}}', escape_typst(title))
        content = content.replace('{{AUTHORS}}', escape_typst(authors))
        content = content.replace('{{ABSTRACT}}', escape_typst(abstract))

        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        temp_dir = tempfile.gettempdir()
        typ_path = os.path.join(temp_dir, f'abstract_{content_hash}.typ')
        png_path = os.path.join(temp_dir, f'abstract_{content_hash}.png')

        try:
            with open(typ_path, 'w') as f:
                f.write(content)

            result = subprocess.run(
                ['typst', 'compile', typ_path, png_path, '--format', 'png'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode != 0:
                raise Exception(f"Typst compilation failed: {result.stderr}")

            with open(png_path, 'rb') as f:
                return f.read()

        finally:
            for path in [typ_path, png_path]:
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

# Test with sample data
bot = TestBot()
title = "A feature-based information-theoretic approach for detecting interpretable, long-timescale pairwise interactions from time series"
authors = "Smith, Johnson, Williams et al"
abstract = "Quantifying relationships between components of a complex network that drives emergent behavior. This is especially critical in understanding the rich dynamics where direct observation of interactions is not feasible, such as in biological networks."

png_bytes = bot._render_with_typst(title, abstract, authors)
print(f"Generated {len(png_bytes)} bytes of PNG data")

# Save for visual inspection
with open('test_output.png', 'wb') as f:
    f.write(png_bytes)
print("Saved to test_output.png")
```

**Step 3: Run test**

```bash
python3 test_typst.py
open test_output.png  # macOS
```

Expected: PNG file created with properly justified text, professional appearance

**Step 4: Clean up test files**

```bash
rm test_typst.py test_output.png
```

---

## Task 5: Integration Testing

**Files:**
- None (manual testing)

**Step 1: Test PIL fallback**

Temporarily rename `typst` binary (if installed):

```bash
# Only if typst is installed
which typst && sudo mv $(which typst) $(which typst).bak
```

Run a test to ensure PIL fallback works:

```python
python3 -c "from paperbot import ArxivBot; print('PIL fallback ready')"
```

Expected: No errors, confirms fallback path exists

Restore typst:

```bash
# Only if you backed it up
[ -f $(which typst).bak ] && sudo mv $(which typst).bak $(which typst)
```

**Step 2: Verify GitHub Actions syntax**

```bash
# Install actionlint if available, or skip
which actionlint && actionlint .github/workflows/post.yml || echo "Skipping actionlint"
```

Expected: No syntax errors (or skip if actionlint not available)

---

## Task 6: Documentation

**Files:**
- Modify: `README.md` (if exists)

**Step 1: Check if README exists**

```bash
[ -f README.md ] && echo "exists" || echo "skip this task"
```

**Step 2: Add Typst note to README (only if exists)**

If README.md exists, add a note about Typst rendering. If not, skip to Step 3.

Look for a section about dependencies or requirements, and add:

```markdown
### Abstract Image Rendering

The bot uses [Typst](https://typst.app/) for professional typesetting of abstract images when available, with automatic fallback to PIL for local development.

- **GitHub Actions**: Typst is automatically installed via `typst-community/setup-typst` action
- **Local development**: Works without Typst (PIL fallback), but installing Typst gives better quality
  - macOS: `brew install typst`
  - Linux: Download from https://github.com/typst/typst/releases
```

**Step 3: Commit documentation**

```bash
# Only if README was modified
git diff --quiet README.md || git add README.md && git commit -m "docs: add Typst rendering information"
```

---

## Task 7: Final Verification and Merge

**Files:**
- None (git operations)

**Step 1: Review all changes**

```bash
git log --oneline origin/master..HEAD
git diff origin/master...HEAD
```

Expected: Should see 3-4 commits (template, Python changes, workflow, optional docs)

**Step 2: Push to remote**

```bash
git push -u origin feature/typst-justification
```

**Step 3: Test in GitHub Actions (manual)**

Trigger the workflow manually via GitHub UI to test Typst installation:
1. Go to Actions tab
2. Select "GH Arxiv Posterbot" workflow
3. Click "Run workflow"
4. Select `feature/typst-justification` branch
5. Watch for successful completion

Expected: Workflow completes successfully, abstract images generated with Typst

**Step 4: Create pull request**

```bash
gh pr create --title "Add Typst-based text justification for abstract images" --body "$(cat <<'EOF'
## Summary
- Replaces PIL manual justification with Typst professional typesetting
- Adds automatic hyphenation and proper word spacing
- Maintains PIL fallback for local development
- Updates GitHub Actions to install Typst

## Testing
- [x] Template compiles successfully
- [x] Python code handles Typst and PIL paths
- [x] GitHub Actions workflow includes Typst setup
- [ ] Manual workflow run on feature branch (pending)

## References
- Design doc: docs/plans/2026-01-01-typst-justification-design.md
EOF
)"
```

Expected: PR created successfully

---

## Success Criteria

- [ ] Template file `abstract_template.typ` created and committed
- [ ] Python code modified with Typst rendering and PIL fallback
- [ ] GitHub Actions workflow updated with Typst installation
- [ ] All commits have clear, descriptive messages
- [ ] Code follows DRY principles (no duplication)
- [ ] YAGNI: No unnecessary features added
- [ ] Local testing confirms fallback works (optional)
- [ ] Changes pushed to feature branch
- [ ] Pull request created

## Notes

- If Typst is not installed locally, skip optional testing tasks - GitHub Actions will be the verification environment
- PIL fallback ensures the bot continues working even if Typst fails
- Template uses cross-platform font (Linux Libertine) with fallback
- Temp file cleanup prevents disk space issues from repeated renders
