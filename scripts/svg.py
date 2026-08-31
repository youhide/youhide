"""Shared chrome for the profile's generated SVG cards.

Every card in assets/ is a Dracula terminal window at 1200px wide. Keeping the
palette, the window frame and the text metrics in one place is what makes the
cards actually identical instead of merely similar.
"""

# Dracula palette — must stay in sync with the hand-written assets/header.svg
BG, BAR, LINE, FG = "#282a36", "#21222c", "#44475a", "#f8f8f2"
COMMENT, PURPLE, PINK, CYAN = "#6272a4", "#bd93f9", "#ff79c6", "#8be9fd"
GREEN, ORANGE, YELLOW, RED = "#50fa7b", "#ffb86c", "#f1fa8c", "#ff5555"

MONO = "ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,DejaVu Sans Mono,monospace"

W = 1200
PAD = 48
INNER = W - 2 * PAD  # 1104 — the usable width inside the card

# Monospace advance width as a fraction of the font size. Every layout decision
# (pill widths, legend spacing, overflow checks) is derived from this.
CHAR = 0.6


def esc(text):
    """Escape text coming from an API before it goes into markup."""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def text_width(text, size):
    return len(str(text)) * size * CHAR


def card(height, title, aria, body, extra_defs=""):
    """Wrap `body` in the standard terminal window."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {height}" width="{W}" height="{height}" role="img" aria-label="{esc(aria)}">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{PURPLE}"/>
      <stop offset="50%" stop-color="{PINK}"/>
      <stop offset="100%" stop-color="{CYAN}"/>
    </linearGradient>
    <pattern id="dots" width="26" height="26" patternUnits="userSpaceOnUse">
      <circle cx="2" cy="2" r="1.2" fill="{LINE}" opacity="0.5"/>
    </pattern>
    <clipPath id="card"><rect width="{W}" height="{height}" rx="18"/></clipPath>{extra_defs}
  </defs>

  <g clip-path="url(#card)" font-family="{MONO}">
    <rect width="{W}" height="{height}" fill="{BG}"/>
    <rect width="{W}" height="{height}" fill="url(#dots)"/>

    <rect width="{W}" height="46" fill="{BAR}"/>
    <circle cx="34" cy="23" r="7" fill="{RED}"/>
    <circle cx="58" cy="23" r="7" fill="{YELLOW}"/>
    <circle cx="82" cy="23" r="7" fill="{GREEN}"/>
    <text x="{W // 2}" y="28" text-anchor="middle" font-size="15" fill="{COMMENT}">{esc(title)}</text>

{body}

    <rect x="0" y="{height - 6}" width="{W}" height="6" fill="url(#accent)"/>
  </g>
</svg>
"""


def prompt(command, y=88, size=22):
    """The `$ command` line every card opens with."""
    return (
        f'    <text x="{PAD}" y="{y}" font-size="{size}">'
        f'<tspan fill="{GREEN}">$</tspan>'
        f'<tspan fill="{FG}" dx="12">{esc(command)}</tspan></text>'
    )


def section(label, y):
    return f'    <text x="{PAD}" y="{y}" font-size="13" fill="{COMMENT}">// {esc(label)}</text>'


def note(text, y):
    return f'    <text x="{PAD}" y="{y}" font-size="13" fill="{COMMENT}"># {esc(text)}</text>'


def pill(x, y, label, color, height=30, size=14):
    """A rounded chip: brand-coloured dot plus the technology name."""
    label = str(label)
    width = 20 + 12 + text_width(label, size) + 16
    return (
        f'<g><rect x="{x:.1f}" y="{y}" width="{width:.1f}" height="{height}" rx="6" '
        f'fill="{BAR}" stroke="{LINE}" stroke-width="1.5"/>'
        f'<circle cx="{x + 16:.1f}" cy="{y + height / 2:.1f}" r="5" fill="{color}"/>'
        f'<text x="{x + 28:.1f}" y="{y + height / 2 + size * 0.36:.1f}" font-size="{size}" '
        f'fill="{FG}">{esc(label)}</text></g>',
        width,
    )
