---
name: "私人账本"
description: "A restrained pastel ledger for traceable personal amounts."
colors:
  bg: "#fafcfb"
  ink: "#354c55"
  muted: "#526771"
  line: "#d8e3df"
  mint: "#aedbc8"
  primary: "#285e4b"
  blue: "#bed4ed"
  peach: "#f3cbb8"
  pink: "#e8b9d1"
  purple: "#cbbfe8"
  surface: "#fff"
  focus: "#236d94"
  error: "#943f3f"
  hover-wash: "#edf5f1"
  primary-hover: "#1c4939"
  tabs-wash: "#eaf1ed"
  field-border: "#a7bbb1"
typography:
  metric:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "clamp(1.25rem, 2.6vw, 2.2rem)"
    fontWeight: 600
  headline:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "1.5rem"
    fontWeight: 650
    letterSpacing: ".02em"
  title:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "1.15rem"
    fontWeight: 650
  body:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: ".875rem"
    fontWeight: 600
  supporting:
    fontFamily: "\"Noto Sans SC\", \"PingFang SC\", \"Microsoft YaHei\", sans-serif"
    fontSize: ".875rem"
    fontWeight: 400
rounded:
  swatch: "3px"
  badge: "4px"
  field: "6px"
  control: "8px"
  tabs: "9px"
  inset: "10px"
  surface: "14px"
spacing:
  step-4: "4px"
  step-8: "8px"
  step-12: "12px"
  step-16: "16px"
  step-18: "18px"
  step-24: "24px"
  step-28: "28px"
  step-36: "36px"
  step-48: "48px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.surface}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  button-secondary-hover:
    backgroundColor: "{colors.hover-wash}"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.field}"
    padding: "8px 10px"
  navigation:
    backgroundColor: "{colors.tabs-wash}"
    rounded: "{rounded.tabs}"
    padding: "4px"
  overview:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.surface}"
    padding: "22px 28px"
  special-chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "9px 16px"
  category-row:
    textColor: "{colors.ink}"
    rounded: "0"
    padding: "12px 4px"
  transaction-row:
    textColor: "{colors.ink}"
    rounded: "0"
    padding: "14px 4px"
---

# Design System: 私人账本

## Overview

**Creative North Star: "The Quiet Personal Ledger"**

The personal ledger uses cool paper, dark ink and restrained pastel category marks. Familiar labeled controls and aligned amounts make checking a private record feel calm and direct. Financial values remain the visual subject; the interface supports tracing them to individual records.

This is a form-led, single-owner web application. White containers and fine dividers organize useful density; color identifies categories and interaction without turning the page into a promotional surface. The same standard Chinese sans stack serves headings, labels and numbers, with no external font requests.

**Key Characteristics:**
- Cool paper and dark ink with soft category colors.
- Direct labeled controls and visible keyboard focus.
- Aligned tabular amounts with readable supporting context.
- Flat sections, lightly bounded containers and scrollable dialogs.
- Desktop paired chart/list and mobile stacked content.

## Colors

A cool near-white ground and dark blue-grey ink support a quiet family of pastel category colors. The frontmatter values are normative and mirror the implemented CSS.

### Primary
- **Ledger Green** (`primary`): the import and save actions, links and input caret; its darker hover variant keeps the action readable.
- **Soft Mint** (`mint`): category identity, selection and annual trend bars.

### Secondary
- **Powder Blue** (`blue`) and **Soft Peach** (`peach`): distinct category fills and matching legend marks.

### Tertiary
- **Dusty Pink** (`pink`) and **Soft Lavender** (`purple`): additional category identities within the same restrained family.

### Neutral
- **Cool Paper** (`bg`): page background.
- **White Surface** (`surface`): overview, fields, buttons and dialog surfaces.
- **Blue-grey Ink** (`ink`): headings, labels, values and chart labels.
- **Supporting Slate** (`muted`): metadata, explanatory copy and percentages.
- **Quiet Divider** (`line`): container edges and list separators.
- **Hover Wash** (`hover-wash`) and **Range Wash** (`tabs-wash`): gentle interaction and grouping surfaces.
- **Field Border** (`field-border`): persistent field boundaries.
- **Focus Blue** (`focus`): keyboard outlines; **Error Red** (`error`): readable inline error text.

**The Ink Rule.** Keep readable labels and amounts in dark ink; use pastel fills for category identity rather than body text.

## Typography

**Display and Body Font:** the installed Noto Sans SC, PingFang SC, Microsoft YaHei, sans-serif stack. No separate display or monospaced family is introduced.

**Character:** standard Chinese sans type keeps controls familiar and financial copy legible. Weight and size establish hierarchy; values use tabular numerals rather than a decorative face.

### Hierarchy
- **Metric:** responsive emphasis from the frontmatter metric role; mobile values use (1.9rem), reducing to (1.5rem) at the smallest breakpoint.
- **Headline:** compact application identity from the headline role.
- **Title:** section and dialog headings from the title role; subordinate headings use (1.05rem).
- **Body:** regular text from the body role; explanatory disclosure paragraphs are limited to (72ch).
- **Label:** semibold field labels from the label role.
- **Supporting:** regular metadata and percentages from the supporting role; dense transaction metadata uses (.8rem).

**The Local Type Rule.** Use the installed Chinese sans stack and tabular numerals for amounts; do not fetch external fonts.

## Layout

A centered content shell has a maximum width of (1260px) with horizontal padding of (36px). Header actions wrap. Sections use a practical rhythm of compact (8–16px) control gaps and larger (24–48px) grouping spaces. Financial overview values occupy three equal columns with divider strokes; the category chart and its complete list occupy two equal columns separated by (48px).

At (760px) and below, shell padding becomes (18px), header and toolbar stack, filters form two columns with the currency field spanning both, overview metrics stack, chart/list become one column and paired form fields stack. Transaction dates sit above descriptions and right-aligned amounts. Annual trend cells change from six columns to two. At (360px) and below, metric labels and amounts stack within their rows.

Dialogs use a normal maximum width of (620px) or wide import width of (920px), always retain (24px) total viewport clearance, and cap height at (90dvh). Their content scrolls vertically with a sticky heading. Keep long descriptions, identifiers and amounts contained through wrapping and minimum-width-safe grid columns.

The current dashboard moves from range controls and summary to coverage, separately reported types, categories and transaction records; the annual mode adds a month grid and a latest-import date in its scope heading. This is an implemented surface sequence, not a required template for every future screen.

## Elevation & Depth

Depth is mostly flat: paper, white surfaces, thin borders and tonal insets. The active range tab receives a small selection shadow; dialogs receive the structural shadow and translucent backdrop. Ordinary transaction and category rows remain flat.

### Shadow Vocabulary
- **Active range tab** (`0 2px 6px #354c5510`): a restrained lift inside the tonal tab track.
- **Modal dialog** (`0 15px 60px #354c5525`): separation of a focused form from the underlying ledger.
- **Modal backdrop** (`#253c4655`): subdued context behind a dialog.

**The Quiet Depth Rule.** Use borders and tonal surfaces for ordinary content; reserve structural elevation for modal dialogs and the active range tab.

## Shapes

Small, softly rounded controls sit within larger rounded containers. Fields use the field radius, buttons the control radius, tab tracks the tabs radius, insets the inset radius, and overview/dialog surfaces the surface radius from frontmatter. Category swatches are small rounded squares. Lists use flat rectangular rows and bottom dividers rather than separate cards for every record.

Borders are generally (1px); keyboard outlines are (3px) with a (3px) offset. Preserve the form-control silhouette and keep touchable controls at a minimum height of (44px).

## Components

### Buttons

Familiar, bounded actions. Primary buttons use ledger green with white text; secondary buttons use white with ink text and quiet borders. Both use the control radius and frontmatter padding. Secondary hover adds the pale wash and a stronger border; pressed secondary buttons use a deeper wash. Primary hover darkens the fill. Disabled buttons have opacity (.55) and a wait cursor.

Keyboard focus uses the shared blue outline. Background and border transitions last (.16s) with `ease-out` only when reduced motion is not requested; reduced-motion mode disables transitions and animations.

### Chips

Separately reported transaction types use compact outlined action buttons with a label and tabular amount, wrapping naturally across the section. Their shape and states follow secondary buttons; the label uses supporting text size. They filter the transaction list rather than changing the headline income/consumption calculation.

### Cards / Containers

The overview uses a white surface, quiet border and surface radius, with desktop padding from frontmatter and mobile padding of (18px). Drilldown panels use a pale wash and inset radius. Empty states are quiet tonal containers with explanatory text. Annual trend cells use a quiet border, control radius and (12px) padding; mint bars are thin (7px) indicators.

### Inputs / Fields

White fields have persistent field borders, the field radius, and frontmatter padding. Labels sit above fields with a (5px) gap. Textareas allow vertical resizing and start at (90px) minimum height. Errors appear as inline red text within the relevant form; notices use pale wash, quiet borders and polite status semantics. Focus remains visible on all keyboard-operable controls.

### Navigation

Monthly and annual range buttons sit inside a padded tonal track. The active button is white with the small selection shadow, communicates selection with `aria-pressed`, and stays a minimum (80px) wide. This range control remains compact on mobile while filters move below it. The skip link becomes visible on focus.

### Category Chart and List

Pastel sectors and matching swatches convey the same category identity. The complete list carries names, tabular amounts and percentages and remains a usable alternative to chart interaction. Chart sectors support keyboard activation and accessible names; hover emphasizes their ink stroke. Labels are shown only for shares at least (3%), with leader lines and separation; smaller sectors remain present and retain complete values in the list. List rows are at least (54px) tall with bottom dividers.

### Transaction Rows and Dialogs

Flat clickable rows organize date, description with supporting context, and right-aligned tabular amount. Rows are at least (76px) tall and turn into a compact two-column arrangement with a separate date line on mobile. Detail dialogs place source links and original record context alongside labeled correction fields, using the same controls and scroll behavior as other forms.

## Do's and Don'ts

### Do:
- **Do** preserve the cool paper, dark ink and confirmed pastel palette.
- **Do** provide explicit labels, visible keyboard focus and at least 44px control targets.
- **Do** keep amounts aligned and use tabular numerals.
- **Do** stack paired content and forms on narrow screens, and let dialogs scroll within the viewport.
- **Do** show missing coverage and source context as readable information.

### Don't:
- **Don't** introduce external font calls or decorative display typography.
- **Don't** use pale category colors for essential text.
- **Don't** replace the direct ledger controls with a marketing hero.
- **Don't** make missing records look like confirmed zero spending.
- **Don't** add heavy shadows, gradients or motion to ordinary ledger sections.
