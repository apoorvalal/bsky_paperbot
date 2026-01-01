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
