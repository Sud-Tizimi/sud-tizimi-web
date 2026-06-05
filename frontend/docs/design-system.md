# Sud-Tizimi — Design System Specification

> **Source of truth:** This document is the formal extraction of the design system shipped in `frontend/tailwind.config.ts`, `frontend/src/styles/globals.css`, and the React component library under `frontend/src/components/`.
> **Source identifier:** Stitch project `12139961574422030019` (Sud-Tizimi Dashboard).
> **Design system name (internal):** *"Justice Infrastructure"*.
> **Audience:** Multiple frontend teams implementing independent modules against the same platform.
> **Stack:** React 18 + TypeScript + TailwindCSS 3.4 + Vite. Icons: `lucide-react`. Font: `@fontsource/inter` and `@fontsource/jetbrains-mono`.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Color System](#2-color-system)
3. [Typography System](#3-typography-system)
4. [Spacing System](#4-spacing-system)
5. [Grid & Layout System](#5-grid--layout-system)
6. [Component Specifications](#6-component-specifications)
7. [Iconography](#7-iconography)
8. [Shadows & Depth](#8-shadows--depth)
9. [Motion System](#9-motion-system)
10. [Responsive Rules](#10-responsive-rules)
11. [Accessibility](#11-accessibility)
12. [Screen Map](#12-screen-map)
13. [Design Tokens for Tailwind](#13-design-tokens-for-tailwind)
14. [Implementation Rules](#14-implementation-rules)

---

## 1. Design Philosophy

### 1.1 Visual Identity
- **Modern Enterprise Minimalism.** The interface reads as infrastructure software for a public institution — not a consumer product, not a marketing site.
- **Authoritative but accessible.** The system has a strong dark structural sidebar (`navy-700`) that anchors the page; the content area is light and quiet so the data carries the visual weight.
- **Minimal decoration.** No gradients, no glass, no drop-shadows on content surfaces. Tonal layering (successive light blue-grey surfaces) is the only depth technique.
- **High readability.** Generous line-height, tabular numerics, restrained palette.
- **Fast operational interface.** Buttons, metrics, and transcripts are designed for someone scanning quickly under time pressure.

### 1.2 UI Personality
- **Quiet, professional, government-grade.** No marketing tone, no playful copy.
- **Identity is the navy sidebar + indigo primary.** Everything else recedes.
- Tables and metrics are the hero. Illustrations, marketing visuals, and decorative imagery are not part of the system.

### 1.3 UX Philosophy
- **Information density over whitespace theatre.** Cards pack data; rows of the table fit a full hearing context in one view.
- **Single primary action per surface.** A "Start Session" call-to-action lives only on the dashboard and the sessions idle state.
- **No modal stacks.** Toasts, inline errors, and full-page states are preferred.
- **No destructive flows in CP1.** The MVP shows read-mostly data plus one streaming-action surface (sessions).

### 1.4 Interaction Philosophy
- **Hover = subtle tonal shift**, not motion. `hover:bg-white/5` on the sidebar, `hover:bg-surface-container-low` on table rows.
- **Active = filled tonal step.** Active nav item gets a `bg-white/10` background and a 2px primary left bar.
- **Click feedback is the focus ring**, not a scale or bounce animation.
- **Real-time feedback is the only "alive" surface**: the live session card pulses, the live badge dot pulses, the audio meter animates.

### 1.5 Visual Hierarchy
- **H1 page title** (`text-headline-lg`, 32px) — one per page.
- **H2 section title** (`text-title-lg`, 18px) — inside cards.
- **Body** (`text-body-md`, 14px / `text-body-lg`, 16px) — content.
- **Mono / metadata** (`text-mono`, 12px uppercase) — labels in tables, system keys, case numbers, timestamps.
- Hierarchy is established by size + weight, not by colour or by shadow.

### 1.6 Density Level
- **Comfortable-density.** 16–20px row padding, 24–32px card padding, 8–16px element gaps. Not compact like a spreadsheet; not airy like a landing page.

### 1.7 Information Architecture
- **Three-pane shell:** fixed left sidebar, sticky topbar, scrolling content area.
- **Card-based content blocks.** No multi-column magazine layouts.
- **Single primary navigation context** at a time (the sidebar); secondary actions live in the page header (`PageHeader`) or are inline.

---

## 2. Color System

All colour tokens are defined in `tailwind.config.ts` under `theme.extend.colors`. Tokens are mandatory — do not introduce new hex values inline.

### 2.1 Brand — Primary (Indigo)

The primary scale is the brand indigo. The dashboard uses `primary-500` for the brand mark container and `primary-600` for the primary button.

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `primary-50` | `#E2DFFF` | Brand-tinted surface (stat-card icon, alert info) | — | — | — |
| `primary-100` | `#C3C0FF` | Info badge border | — | — | — |
| `primary-200` | `#9D98FF` | Active-session banner border, judge role pill border | — | — | — |
| `primary-300` | `#7A72FF` | Reserved | — | — | — |
| `primary-400` | `#5C50F0` | Reserved | — | — | — |
| `primary-500` | `#4F46E5` | Brand mark container, stat-card icon, active nav rail bar, primary badge dot | `primary-600` | `primary-700` | `primary-200` |
| `primary-600` | `#3525CD` | Primary button hover, primary text on primary-50 | `primary-700` | — | — |
| `primary-700` | `#2A1FA8` | Primary button active, primary text on pill (judge) | — | — | — |
| `primary-800` | `#1F1780` | Reserved | — | — | — |
| `primary-900` | `#150F58` | Reserved | — | — | — |

Tailwind class: `bg-primary-{50..900}` / `text-primary-{50..900}` / `border-primary-{50..900}` / `ring-primary-500`.

### 2.2 Sidebar — Navy

The dark structural sidebar is built from `navy-700`. The other navy stops exist for the case status palette and inactive states.

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `navy-DEFAULT` | `#0F172A` | Reserved | — | — | — |
| `navy-50` | `#EAF1FF` | Reserved | — | — | — |
| `navy-100` | `#D3E4FE` | Surface variant | — | — | — |
| `navy-200` | `#A6BFE3` | Reserved | — | — | — |
| `navy-300` | `#7897C2` | Reserved | — | — | — |
| `navy-400` | `#4A6FA1` | Reserved | — | — | — |
| `navy-500` | `#213145` | Reserved | — | — | — |
| `navy-600` | `#172033` | Reserved | — | — | — |
| `navy-700` | `#0F172A` | **Sidebar background** | — | — | — |
| `navy-800` | `#0B1C30` | Body / on-surface default (`ink.DEFAULT` mirrors this) | — | — | — |
| `navy-900` | `#0B1C30` | Reserved | — | — | — |

Tailwind class: `bg-navy-{50..900}`.

### 2.3 Status / Success — Emerald

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `emerald-50` | `#E6FBF1` | Online system pill background, success soft surface | — | — | — |
| `emerald-100` | `#6FFBBE` | Success badge background, success icon background | — | — | — |
| `emerald-200` | `#4EDEA3` | Success badge border | — | — | — |
| `emerald-300` | `#10B981` | Brand emerald (delta-up, success dot) | — | — | — |
| `emerald-400` | `#0E9968` | Reserved | — | — | — |
| `emerald-500` | `#10B981` | Audio meter low band, delta-up text | — | — | — |
| `emerald-600` | `#005338` | Success pill text, online system text | — | — | — |
| `emerald-700` | `#003824` | Reserved | — | — | — |

Tailwind class: `bg-emerald-{50..700}` / `text-emerald-{...}` / `border-emerald-{...}`.

### 2.4 Surfaces (Light Theme)

Surfaces are tonal layers of blue-tinted off-white. There is no "dark mode" in CP1.

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `surface.DEFAULT` | `#F8F9FF` | App background (`<body>`), page background | — | — | — |
| `surface.dim` | `#CBDBF5` | Reserved | — | — | — |
| `surface.bright` | `#F8F9FF` | Reserved | — | — | — |
| `surface.container-lowest` | `#FFFFFF` | Top bar, cards, speaker list background | — | — | — |
| `surface.container-low` | `#EFF4FF` | Table row hover, speaker-list alt surface | — | — | — |
| `surface.container` | `#E5EEFF` | Language switcher background, idle-stop icon background | — | — | — |
| `surface.high` | `#DCE9FF` | Reserved | — | — | — |
| `surface.highest` | `#D3E4FE` | Reserved | — | — | — |
| `surface.variant` | `#D3E4FE` | Reserved | — | — | — |

Tailwind class: `bg-surface`, `bg-surface-container`, `bg-surface-container-low`, `bg-surface-container-lowest`, `bg-surface-high`, `bg-surface-highest`.

### 2.5 Ink (Typography)

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `ink.DEFAULT` | `#0B1C30` | All primary text, headings, body | — | — | — |
| `ink.muted` | `#464555` | Secondary text (subtitle, hints, metadata) | — | — | — |
| `ink.subtle` | `#5C647A` | Reserved | — | — | — |

Tailwind class: `text-ink`, `text-ink-muted`, `text-ink-subtle`.

### 2.6 Outline (Borders & Dividers)

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `outline.DEFAULT` | `#777587` | Strong outline (table column rule when needed) | — | — | — |
| `outline.variant` | `#C7C4D8` | Scrollbar thumb | — | — | — |
| `outline.soft` | `#E2E8F0` | Card border, table row divider, input border | `outline.DEFAULT` on focus | — | — |

Tailwind class: `border-outline`, `border-outline-variant`, `border-outline-soft`.

### 2.7 Error

| Token | Hex | Usage | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- |
| `error.DEFAULT` | `#BA1A1A` | Primary danger (Stop button, live dot, error text) | `error.DEFAULT/90` | — | — |
| `error.container` | `#FFDAD6` | Live-session status bar background, live-badge background, error-icon background | — | — | — |
| `error.on` | `#FFFFFF` | Text on solid error button | — | — | — |
| `error.onContainer` | `#93000A` | Text on `error.container` (error badge) | — | — | — |

Tailwind class: `bg-error`, `bg-error-container`, `text-error`, `text-error-on`, `text-error-onContainer`, `border-error`.

### 2.8 Speaker-Role Palette (Tailwind defaults, not in `colors`)

The five speaker roles use Tailwind's default 50/500/700 ramps. These are the only role-distinguishing colours in the system.

| Role | Background | Text | Accent (dot, bar) | Border |
| --- | --- | --- | --- | --- |
| Judge | `bg-primary-50` | `text-primary-700` | `bg-primary-500` | `border-primary-200` |
| Plaintiff | `bg-amber-50` | `text-amber-700` | `bg-amber-500` | `border-amber-200` |
| Defendant | `bg-rose-50` | `text-rose-700` | `bg-rose-500` | `border-rose-200` |
| Witness | `bg-sky-50` | `text-sky-700` | `bg-sky-500` | `border-sky-200` |
| Lawyer | `bg-violet-50` | `text-violet-700` | `bg-violet-500` | `border-violet-200` |
| Unknown | `bg-surface-container` | `text-ink-muted` | `bg-ink-muted` | `border-outline-soft` |

Defined in `src/lib/speakerStyles.ts` as `ROLE_STYLES` and consumed by the speaker list, transcript pills, and speaking indicator.

### 2.9 Audio Meter Palette

| Band | Bars (out of 24) | Token |
| --- | --- | --- |
| Low (green) | 0–15 | `bg-emerald-500` |
| Mid (amber) | 16–20 | `bg-amber-500` |
| High (red) | 21–23 | `bg-error` |
| Off | n/a | `bg-outline-soft` |

---

## 3. Typography System

Fonts loaded in `globals.css`: Inter (400/500/600/700) and JetBrains Mono (400/500/600).

### 3.1 Font Family

| Token | Stack | Use |
| --- | --- | --- |
| `font-sans` | `Inter, ui-sans-serif, system-ui, sans-serif` | All UI text, headings, body |
| `font-mono` | `"JetBrains Mono", ui-monospace, SFMono-Regular, monospace` | Case numbers, IDs, timestamps, metrics, language-switcher labels |

### 3.2 Type Scale

| Token | Size | Line Height | Letter Spacing | Weight | Tailwind Class | Usage Example |
| --- | --- | --- | --- | --- | --- | --- |
| `display-lg` | 48px (3rem) | 56px (3.5rem) | -0.02em | 700 | `text-display-lg` | Reserved for hero / marketing; not used in CP1 |
| `headline-lg` | 32px (2rem) | 40px (2.5rem) | -0.01em | 600 | `text-headline-lg` | Page `<h1>` (Dashboard title) |
| `headline-lg-mobile` | 24px (1.5rem) | 32px (2rem) | -0.01em | 600 | `text-headline-lg-mobile` | Optional mobile page title |
| `headline-md` | 24px (1.5rem) | 32px (2rem) | default | 600 | `text-headline-md` | Card section title, stat-card value, idle-view heading |
| `title-lg` | 18px (1.125rem) | 28px (1.75rem) | default | 600 | `text-title-lg` | Card title, sub-section heading, live case title |
| `body-lg` | 16px (1rem) | 24px (1.5rem) | default | 400 | `text-body-lg` | Default body, transcript entries, idle description |
| `body-md` | 14px (0.875rem) | 20px (1.25rem) | default | 400 | `text-body-md` | Table cells, secondary body, button label (sm/md) |
| `label-md` | 12px (0.75rem) | 16px (1rem) | default | 500 | `text-label-md` | Badge text, table header text (raw), small labels |
| `caption` | 12px (0.75rem) | 16px (1rem) | default | 400 | `text-caption` | Metadata, case number in list, hint text |

### 3.3 Utility / Composite Tokens

| Class | Definition | Use |
| --- | --- | --- |
| `text-mono` | `font-mono text-label-md tracking-wide uppercase` | All table column headers, system keys (STT, STATUS), live banner "LIVE" pill |
| `tabular-nums` | `font-variant-numeric: tabular-nums` | All numeric metrics, durations, case numbers, table cell durations |

### 3.4 Typographic Rules
- All numbers (durations, counts, case numbers) must use `font-mono` + `tabular-nums`.
- All metadata keys in tables use `text-mono` (uppercase mono 12px, `text-ink-muted`).
- Page titles use `text-headline-lg` with `tracking-tight` already baked in.
- Body text colour: `text-ink`. Subdued: `text-ink-muted`. Mute-on-mute: `text-ink-muted/70`.
- Do not introduce a new size; use the closest existing token.

---

## 4. Spacing System

The grid is a **4px baseline**. Tailwind's default scale (1 = 4px) is used throughout. Custom spacing tokens extend it where needed.

### 4.1 Base Spacing Tokens

| Tailwind | px | Use |
| --- | --- | --- |
| `0.5` | 2 | Inner micro-gap (badge dot gap) |
| `1` | 4 | Reserved (rare) |
| `1.5` | 6 | Icon-to-text gap in inline elements |
| `2` | 8 | Default small gap, button gap (`gap-2`) |
| `2.5` | 10 | Speaker-list inner padding |
| `3` | 12 | Card inner padding option `sm`, table cell padding horizontal (`px-3`) |
| `3.5` | 14 | Reserved |
| `4` | 16 | Card section gap, button height = 16 + content |
| `4.5` | 18 (1.125rem) | Custom; nav-item icon-to-label |
| `5` | 20 | Top-bar height-1 padding, list-row vertical padding (`py-3` is 12) |
| `6` | 24 | Page padding (`p-6`), card padding `md`, table-cell horizontal padding (`px-6`) |
| `7` | 28 | Reserved |
| `8` | 32 | Page padding at `md:` (`p-8`), card padding `lg`, `mb-8` page-header offset |
| `10` | 40 | Reserved |
| `12` | 48 | Empty-state padding |
| `16` | 64 | Reserved |
| `sidebar` | 280 (custom) | `<aside>` width |
| `topbar` | 64 (4rem, custom) | `<header>` height |
| `gutter` | 20 (1.25rem, custom) | Reserved; intra-card section gap is normally `gap-4` (16) |

### 4.2 Container / Page Padding

| Surface | Mobile (`<768px`) | Desktop (`≥768px`) |
| --- | --- | --- |
| Page wrapper | `p-6` (24px) | `p-8` (32px) |
| Card padding `none` | 0 | 0 |
| Card padding `sm` | 16px | 16px |
| Card padding `md` (default) | 24px | 24px |
| Card padding `lg` | 32px | 32px |
| Page wrapper max width | none (full-bleed) | `max-w-screen-2xl` |
| ComingSoon page | `p-6 md:p-8 max-w-2xl mx-auto` | as left |

### 4.3 Component Internal Spacing

| Component | Token | Value |
| --- | --- | --- |
| Sidebar logo block | `h-16 px-6` (64 × 24) | — |
| Sidebar nav padding | `px-3 py-4` | — |
| Sidebar nav gap between items | `gap-1` (4) | — |
| Sidebar nav item | `h-10 px-3` (40 × 12) | — |
| Topbar | `h-16 px-6 gap-4` | — |
| PageHeader row gap | `gap-4` | — |
| PageHeader bottom margin | `mb-8` (32) | — |
| Card header to body | `mb-4` (16) | — |
| Subsystem card to subsystem card | `gap-4` (16) | — |
| Transcript entries gap | `gap-4` (16) | — |
| Speaker list gap | `gap-2` (8) | — |
| Recent sessions list row | `px-6 py-3 gap-4` | — |

### 4.4 Mobile Adjustments
- `p-6` → `p-8` at `md` (768px).
- Topbar `h-16 px-6` unchanged; the system-status pill and language switcher are `hidden md:inline-flex`.
- Sidebar is `hidden lg:flex`; on `<lg` there is no navigation drawer in CP1 (CP2 brings the mobile shell).

---

## 5. Grid & Layout System

### 5.1 Desktop Layout Structure

```
┌────────────────────────────────────────────────────────────────────────┐
│  <body class="bg-surface text-ink">                                     │
│  ┌──────────────┐ ┌────────────────────────────────────────────────┐   │
│  │  <Sidebar/>  │ │  <TopBar/>         (h-16 sticky top-0 z-10)     │   │
│  │ w-sidebar    │ ├────────────────────────────────────────────────┤   │
│  │ (280px)      │ │  <main class="flex-1 min-w-0 overflow-x-hidden">│   │
│  │ bg-navy-700  │ │    <div class="p-6 md:p-8 max-w-screen-2xl">     │   │
│  │ flex-col     │ │      <PageHeader/>                              │   │
│  │ text-white   │ │      ... page content ...                        │   │
│  │ hidden lg:   │ │    </div>                                        │   │
│  │ flex         │ │  </main>                                         │   │
│  └──────────────┘ └────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────┘
```

Defined by `AppShell.tsx`:
- Outer: `min-h-screen flex bg-surface`
- Sidebar: `hidden lg:flex w-sidebar shrink-0 flex-col bg-navy-700 text-white`
- Right column: `flex-1 min-w-0 flex flex-col`
- Main: `flex-1 min-w-0 overflow-x-hidden`

### 5.2 Mobile Layout Structure
- Sidebar is **hidden below `lg`** (1024px). No mobile drawer in CP1.
- Topbar remains and keeps the search input (disabled), help icon, and (when ≥`md`) the system status pill and language switcher.
- Content uses the same `p-6 md:p-8 max-w-screen-2xl` wrapper, so it reflows identically.

### 5.3 Breakpoints

Default Tailwind breakpoints. Active usages in this codebase:

| Breakpoint | min-width | Used for |
| --- | --- | --- |
| `sm` | 640px | Subsystem 3-column collapse to 1, table column visibility |
| `md` | 768px | Page padding switch, topbar system-pill + language switcher visibility |
| `lg` | 1024px | Sidebar visibility, transcript 2-column body, idle-view two-column |
| `xl` | 1280px | Reserved |
| `2xl` | 1536px | `max-w-screen-2xl` page wrapper cap |

### 5.4 Grid Columns

| Surface | Mobile | sm | md | lg+ |
| --- | --- | --- | --- | --- |
| System Status — subsystem row | 1 | 3 | 3 | 3 |
| Active session banner | flex-col | flex-col | flex-col | flex-row |
| Cases — summary tiles | 1 | 2 | 2 | 2 |
| Recent sessions table | full | cols visible by `hidden sm:table-cell` |
| Live session — body | 1 (stacked) | 1 | 1 | `1fr / 320px` |

### 5.5 Content Max Widths

| Element | Max width | Class |
| --- | --- | --- |
| Standard page | 1536px (screen-2xl) | `max-w-screen-2xl` |
| ComingSoon | 672px (2xl) | `max-w-2xl mx-auto` |
| Topbar search field | 576px (xl) | `max-w-xl` |
| Sidebar | 280px | `w-sidebar` |
| Speaker panel (live) | 320px | `lg:grid-cols-[1fr_320px]` |

### 5.6 Gutter
- Section gap inside a page: `gap-4` (16) or vertical `space-y-6` (24).
- Card-to-card gap: `mb-6` (24) or `gap-4` (16) when in a grid.

---

## 6. Component Specifications

### 6.1 Button

**Source:** `src/components/ui/Button.tsx`. Variants: `primary | secondary | ghost | danger`. Sizes: `sm | md | lg`.

| Property | sm | md | lg |
| --- | --- | --- | --- |
| Height | 32px (`h-8`) | 40px (`h-10`) | 48px (`h-12`) |
| Horizontal padding | 12px (`px-3`) | 16px (`px-4`) | 24px (`px-6`) |
| Font | `text-body-md` | `text-body-lg` | `text-body-lg` |
| Icon gap | 6px (`gap-1.5`) | 8px (`gap-2`) | 8px (`gap-2`) |
| Radius | 4px (`rounded`) | 8px (`rounded-lg`) | 8px (`rounded-lg`) |

**Variants:**

| Variant | Background | Text | Border | Hover | Active | Disabled |
| --- | --- | --- | --- | --- | --- | --- |
| `primary` | `primary-500` | `white` | `primary-500` | bg+border `primary-600` | bg+border `primary-700` | bg+border `primary-200`, `cursor-not-allowed` |
| `secondary` | `white` | `ink` | `outline-soft` | border `outline`, bg `surface-container-low` | — | `opacity-50 cursor-not-allowed` |
| `ghost` | `transparent` | `ink` | `transparent` | bg `surface-container-low` | — | `opacity-50 cursor-not-allowed` |
| `danger` | `error` | `error-on` | `error` | `bg-error/90` | — | `opacity-50 cursor-not-allowed` |

**Common rules:**
- `font-medium`, `transition-colors duration-150`.
- Focus: `focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface`.
- Icons: `shrink-0` on the left/right slot, 16px in `sm`, 20px in `md/lg`.
- `fullWidth` adds `w-full`.

### 6.2 IconButton

**Source:** `src/components/ui/IconButton.tsx`. Variants: `ghost | subtle`. Sizes: `sm | md | lg`. Requires `label` for a11y (`aria-label` + `title`).

| Size | Dimensions |
| --- | --- |
| `sm` | 32×32 (`h-8 w-8`) |
| `md` (default) | 40×40 (`h-10 w-10`) |
| `lg` | 48×48 (`h-12 w-12`) |

| Variant | Default text | Hover |
| --- | --- | --- |
| `ghost` | `text-ink` | `hover:bg-surface-container-low` |
| `subtle` (default) | `text-ink-muted` | `hover:text-ink hover:bg-surface-container-low` |

- Radius: `rounded-md` (6px).
- Focus ring: same as Button.
- Icon sizing: pass the icon as `icon` prop with the desired size (commonly `h-5 w-5` for `md`).

### 6.3 Input (text / search)

**Source:** Inline in `TopBar.tsx`. Pattern used elsewhere should match.

| Property | Value |
| --- | --- |
| Container height | 40px (`h-10`) |
| Container width | `w-full` |
| Border | 1px `outline-soft` |
| Radius | `rounded-md` (6px) |
| Background | `surface` (`#F8F9FF`) |
| Text | `text-body-md text-ink` |
| Placeholder | `text-ink-muted` |
| Padding | `pl-9 pr-3` (search) — left icon at `left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-ink-muted` |
| Focus | `focus:outline-none focus:border-primary-500 focus:ring-2 focus:ring-primary-500/15` |
| Disabled | `disabled` attribute (topbar search is disabled in CP1) |

There is no formal `Input` component in `components/ui/`. The above is the canonical pattern, used as the single source of truth for any new search/text field.

### 6.4 Textarea
**Not used in CP1.** When introduced in CP2: follow the same border, radius, focus and padding rules as the Input.

### 6.5 Select
**Not used as a styled component in CP1.** The language switcher is a button group; the LiveSTT language selector is a 3-button segmented control. There is no native `<select>` styled.

### 6.6 Card

**Source:** `src/components/ui/Card.tsx`. Padding options: `none | sm | md | lg` (16 / 24 / 32 px).

| Property | Value |
| --- | --- |
| Background | `bg-white` |
| Border | 1px `border-outline-soft` |
| Radius | `rounded-lg` (8px) |
| Shadow | `shadow-soft` (see §8) |

- **CardHeader**: `flex items-center justify-between gap-4 mb-4`.
- **CardTitle**: `text-title-lg text-ink` (18px / 600).
- **CardDescription**: `text-body-md text-ink-muted`.
- Padding `none` is used for the live session surface (header + body have their own padding).

### 6.7 StatCard

**Source:** `src/components/ui/StatCard.tsx`. Always wraps a `Card padding="md"`.

| Property | Value |
| --- | --- |
| Container | Card + `flex flex-col gap-3` |
| Label row | `flex items-center justify-between` |
| Label | `text-mono text-ink-muted` (uppercase mono 12) |
| Icon container | `h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center` |
| Value | `text-headline-md text-ink tabular-nums` (24/600) |
| Delta | `text-body-md font-medium tabular-nums`; `up → text-emerald-500`, `down → text-error`, `flat → text-ink-muted`; arrow glyph `↑` / `↓` / `→` |
| Hint | `text-caption text-ink-muted` |

### 6.8 SubsystemCard (Dashboard internal)

A non-shared component rendered only inside the System Status card. Used in the dashboard "subsystems" 3-up.

| Property | Value |
| --- | --- |
| Container | `rounded-md border border-outline-soft bg-white p-4` |
| Icon container | `h-8 w-8 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center` |
| Label | `text-mono text-ink-muted` |
| Value | `text-title-lg text-ink font-semibold` |
| Status dot | 6px circle, color by state: `online → bg-emerald-500`, `degraded → bg-amber-500`, `offline → bg-error` |
| Detail | `text-caption text-ink-muted` |
| Metric row (footer) | top-border `pt-3 border-outline-soft`, `flex items-baseline justify-between`; metric `text-headline-md text-ink font-mono tabular-nums`, label `text-caption text-ink-muted` |

### 6.9 Table

**Source:** Inline in `Dashboard.tsx` and `Cases.tsx`. Both share the same pattern.

| Property | Value |
| --- | --- |
| Wrapper | `overflow-x-auto -mx-6` (counter-card padding for bleed) |
| Element | `<table class="w-full">` |
| Header row | `border-b border-outline-soft` |
| Header cell | `text-mono text-ink-muted h-10 px-6 (or px-3) font-medium`; left aligned |
| Body row | `border-b border-outline-soft last:border-0 hover:bg-surface-container-low transition-colors`; rows are clickable on Cases (`cursor-pointer`) |
| Body cell | `px-6 py-4` for the first column, `px-3 py-4` for the rest |
| First-column content | Icon container `h-9 w-9 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0` (or `bg-error-container text-error` for `in_hearing` cases), then two-line stack: title `text-body-md font-medium text-ink truncate` + subtitle `text-caption font-mono text-ink-muted` |
| Column hiding | Use `hidden sm|md|lg:table-cell` per cell; first + last column always visible |
| Numeric cells | `font-mono tabular-nums` |
| Date cells | `flex items-center gap-1.5 text-body-md text-ink` + `Calendar` icon `h-3.5 w-3.5 text-ink-muted` + value `font-mono tabular-nums` |

### 6.10 Sidebar Item (NavLink)

**Source:** `src/components/layout/Sidebar.tsx`.

| Property | Value |
| --- | --- |
| Container | `<aside class="hidden lg:flex w-sidebar shrink-0 flex-col bg-navy-700 text-white">` |
| Logo block | `h-16 px-6 flex items-center gap-3 border-b border-white/5` |
| Logo mark | `h-9 w-9 rounded-md bg-primary-500` with `ShieldCheck h-5 w-5 text-white` |
| App name | `text-body-lg font-semibold tracking-tight` |
| Tagline | `text-caption text-white/50 uppercase tracking-wider` |
| Nav region | `flex-1 px-3 py-4 overflow-y-auto` |
| Nav list | `flex flex-col gap-1` |
| Item | `flex items-center gap-3 h-10 px-3 rounded-md text-body-md font-medium transition-colors` |
| Item icon | `h-4 w-4 shrink-0` |
| Item default | `text-white/70 hover:text-white hover:bg-white/5` |
| Item active | `bg-white/10 text-white`; renders a left rail `absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-primary-500` |
| User footer | `p-3 border-t border-white/5` |
| User row | `flex items-center gap-3 px-2 py-2 rounded-md` |
| User avatar | `h-9 w-9 rounded-full bg-primary-500/20 text-primary-100 inline-flex items-center justify-center text-body-md font-semibold` (initials) |
| User name | `text-body-md font-medium truncate` |
| User role | `text-caption text-white/50 truncate` |

### 6.11 Top Bar

**Source:** `src/components/layout/TopBar.tsx`.

| Property | Value |
| --- | --- |
| Container | `h-16 bg-white border-b border-outline-soft px-6 flex items-center gap-4 sticky top-0 z-10` |
| Search | full-width up to `max-w-xl`; pattern from §6.3; **disabled in CP1** |
| System status pill | `hidden md:inline-flex items-center gap-2 h-9 px-3 rounded-md border text-body-md`; online → `bg-emerald-50 border-emerald-200 text-emerald-600`; offline → `bg-error-container border-red-200 text-error` |
| System status icon | `Activity h-4 w-4` |
| Language switcher | `hidden md:inline-flex items-center bg-surface-container rounded-md p-0.5`; each button `h-8 px-2.5 rounded text-caption font-mono uppercase tracking-wide`; active → `bg-white text-ink shadow-soft`; inactive → `text-ink-muted hover:text-ink` |
| Help | `IconButton` (subtle, `md`) with `HelpCircle h-5 w-5` |

### 6.12 PageHeader

**Source:** `src/components/layout/PageHeader.tsx`.

| Property | Value |
| --- | --- |
| Container | `flex flex-col gap-4 md:flex-row md:items-center md:justify-between mb-8` |
| Title | `text-headline-lg text-ink tracking-tight` |
| Subtitle | `text-body-lg text-ink-muted mt-1` |
| Actions | `flex items-center gap-3` |

### 6.13 Badge

**Source:** `src/components/ui/Badge.tsx`. Variants: `success | warning | error | info | neutral | live`. Optional `dot`.

| Property | Value |
| --- | --- |
| Container | `inline-flex items-center gap-1.5 px-2.5 h-6 rounded-full border text-label-md uppercase tracking-wide whitespace-nowrap` |

| Variant | Background | Text | Border | Dot color (when used) |
| --- | --- | --- | --- | --- |
| `success` | `emerald-100` | `emerald-600` | `emerald-200` | `emerald-300` |
| `warning` | `amber-50` | `amber-700` | `amber-200` | `amber-500` |
| `error` | `error-container` | `error-onContainer` | `red-200` | `error` |
| `info` | `primary-50` | `primary-600` | `primary-100` | `primary-500` |
| `neutral` | `surface-container` | `ink-muted` | `outline-soft` | `outline` |
| `live` | `error-container` | `error` | `red-200` | `error` + `animate-pulse-dot` |

The dot is 6px (`h-1.5 w-1.5 rounded-full`).

### 6.14 Chip / Pill (Speaker Role)

Not a separate component — defined in `src/lib/speakerStyles.ts` as `ROLE_STYLES`. Inline usage pattern:

| Property | Value |
| --- | --- |
| Container | `inline-flex items-center gap-1.5 h-6 px-2 rounded text-caption font-medium` |
| Background | `style.bg` (role-dependent, see §2.8) |
| Text | `style.text` |
| Side accent dot | `block h-2 w-2 rounded-full style.accent` (used in transcript entries) |

### 6.15 Dropdown / Menu
**Not used in CP1.** When introduced in CP2, treat as a floating `Card` (no shadow upgrade needed) anchored to the trigger. Do not introduce a third-party dropdown library.

### 6.16 Modal / Dialog
**Not used in CP1.** When introduced in CP2:
- Backdrop: `bg-ink/40` (or `navy-800/40`) at `z-40`.
- Panel: `Card padding="lg"` with `max-w-lg` or `max-w-2xl`, centred, `shadow-floating`.

### 6.17 Alert / Inline Status

The pattern used in `LiveSttTest.tsx` (error and result blocks) is the canonical alert surface.

| Type | Container | Icon | Text |
| --- | --- | --- | --- |
| Error | `rounded-md border border-red-200 bg-red-50 p-3` | `AlertCircle h-4 w-4 mt-0.5 shrink-0 text-error` | `text-body-md text-error` |
| Result (neutral) | `rounded-md border border-outline-soft bg-surface-container-low p-4` | `Sparkles` (in CardTitle) | `text-body-lg text-ink` (italic + `text-ink-muted` when empty) |

The system status pill (topbar) is a live alert variant — see §6.11.

### 6.18 Active Session Banner (Dashboard)

| Property | Value |
| --- | --- |
| Container | `<Card padding="md" class="mb-6 border-primary-200 bg-primary-50/30">` |
| Icon container | `h-11 w-11 rounded-md bg-error-container text-error inline-flex items-center justify-center shrink-0` (Mic) |
| Title row | `flex items-center gap-2 flex-wrap mb-1`; title `text-title-lg text-ink truncate`; `<Badge variant="live" dot>Live</Badge>` |
| Subtitle | `text-caption font-mono text-ink-muted` — `caseNumber · judge · speakers detected` |
| Right cluster | elapsed timer `text-mono text-ink-muted` label + `text-headline-md text-ink font-mono tabular-nums` value; `<Button size="lg" leftIcon=Radio>` "Open Session" |

### 6.19 Live Session Card (Sessions page)

| Region | Specification |
| --- | --- |
| Card | `<Card padding="none" class="overflow-hidden">` |
| Status bar | `flex items-center justify-between gap-4 px-5 py-3 bg-error-container border-b border-red-200` |
| Status left | `relative flex h-3 w-3` outer ping ring (`absolute inline-flex h-full w-full rounded-full bg-error opacity-60 animate-ping`) + solid `bg-error` dot + `text-mono text-error` "LIVE" + `text-body-md text-ink font-medium truncate` case title |
| Status right | `flex items-center gap-3 text-body-md text-ink-muted shrink-0` — case number mono, 1px `outline-soft` divider, mono `tabular-nums text-ink` elapsed time |
| Body | `grid grid-cols-1 lg:grid-cols-[1fr_320px] divide-y lg:divide-y-0 lg:divide-x divide-outline-soft` |
| Empty transcript | `h-full flex flex-col items-center justify-center text-center py-16`; icon `h-12 w-12 rounded-full bg-primary-50 text-primary-500`, "Listening…" `text-title-lg text-ink`, helper `text-body-md text-ink-muted mt-1` |

### 6.20 Transcript Entry

| Property | Value |
| --- | --- |
| List | `<ol class="flex flex-col gap-4">` |
| Entry | `flex gap-3 group` |
| Side accent | `shrink-0 pt-1` + `block h-2 w-2 rounded-full` colour from `ROLE_STYLES[role].accent` |
| Header row | `flex items-center gap-2 mb-1` |
| Speaker pill | `inline-flex items-center gap-1.5 h-6 px-2 rounded text-caption font-medium`; bg/text from `ROLE_STYLES` |
| Timestamp | `text-caption font-mono text-ink-muted tabular-nums` — `HH:MM:SS` |
| Listening indicator | `text-caption italic text-ink-muted` — "· listening…" — only when `!entry.isFinal` |
| Body text | `text-body-lg text-ink leading-relaxed`; when `!entry.isFinal` → `opacity-60 italic` |
| Auto-scroll | Stays pinned to bottom while `distanceFromBottom < 40` |

### 6.21 Speaker Card (right panel)

| Property | Value |
| --- | --- |
| Panel | `bg-surface-container-lowest` |
| Panel header | `px-5 py-3 border-b border-outline-soft flex items-center justify-between`; title `text-mono text-ink-muted` "Speaker Identification", counter `text-caption text-ink-muted` "N detected" |
| List | `p-3 flex flex-col gap-2` |
| Empty | `text-body-md text-ink-muted px-2 py-6 text-center` — "Speakers will appear as they speak." |
| Card | `flex items-center gap-3 p-3 rounded-md border transition-colors` |
| Card default | `bg-white border-outline-soft` |
| Card speaking | `style.bg style.border` (per role) |
| Avatar | `h-9 w-9 rounded-full inline-flex items-center justify-center shrink-0`; speaking → `style.bg style.text`; idle → `bg-surface-container text-ink-muted` |
| Name | `text-body-md font-medium text-ink truncate` |
| Role | `text-caption uppercase tracking-wide style.text` |
| Speaking indicator | 3 vertical bars 2px wide; heights 40 / 100 / 60 %; `style.accent` color; `animate-pulse-dot`; bar 2 delay 120ms, bar 3 delay 240ms |

### 6.22 Control Bar (Sessions footer)

| Property | Value |
| --- | --- |
| Container | `<Card padding="md" class="mt-6 sticky bottom-4 z-10">` |
| Row | `flex items-center gap-4` |
| Audio meter | `flex items-center gap-2`; `Volume2 h-4 w-4 text-ink-muted`; 24 bars, `flex items-end gap-0.5 h-7`; bar width `w-1`; radius `rounded-sm`; per-bar height `30 + (i/24) × 70 %`; transition `transition-all duration-75`; colour bands per §2.9 |
| Mute | `<Button variant="secondary" size="md" leftIcon=Mic|MicOff>`; `disabled={!isLive}` |
| Start | `<Button size="lg" leftIcon=Play (h-5 w-5 fill-current)>`; disabled while `isStopping` |
| Stop | `<Button size="lg" variant="danger" leftIcon=Square (h-4 w-4 fill-current)>` |

### 6.23 Audio Meter Bar

| Property | Value |
| --- | --- |
| Container | `flex items-end gap-0.5 h-7` |
| Bar | `w-1 rounded-sm transition-all duration-75` |
| Off bar | `bg-outline-soft` |
| On bar — green | `bg-emerald-500` (bars 0–15) |
| On bar — amber | `bg-amber-500` (bars 16–20) |
| On bar — red | `bg-error` (bars 21–23) |
| Height per bar | inline `style={{ height: ${30 + (i/BARS)*70}% }}` |
| Tooltip | "Microphone muted" / `Input level: N%` |

### 6.24 Idle / Stopping Cards (Sessions)

Both use `<Card padding="lg" class="text-center">`.

**Idle:**
- Icon container: `mx-auto h-14 w-14 rounded-full bg-primary-50 text-primary-500 inline-flex items-center justify-center mb-4`; `Radio h-7 w-7`
- Title: `text-headline-md text-ink mb-2` — "No active session"
- Description: `text-body-lg text-ink-muted max-w-md mx-auto mb-6`
- Action row: `flex items-center justify-center gap-3`; `Button variant="ghost" leftIcon=ArrowLeft` "Back to Dashboard" + `Button size="lg" leftIcon=Play` "Start Session"

**Stopping:**
- Icon container: `mx-auto h-14 w-14 rounded-full bg-surface-container text-ink-muted inline-flex items-center justify-center mb-4`; `Square h-6 w-6`
- Title: `text-headline-md text-ink mb-2` — "Session stopped"
- Description: `text-body-lg text-ink-muted max-w-md mx-auto`

### 6.25 Recent Sessions List (Sessions page, idle context)

| Property | Value |
| --- | --- |
| Container | `<Card padding="md">` with `<CardHeader>` (title only) |
| List | `flex flex-col divide-y divide-outline-soft -mx-6` |
| Row | `flex items-center gap-4 px-6 py-3 hover:bg-surface-container-low` |
| Icon | `h-8 w-8 rounded-md bg-primary-50 text-primary-500 inline-flex items-center justify-center shrink-0`; `Gavel h-4 w-4` |
| Title | `text-body-md font-medium text-ink truncate` |
| Subtitle | `text-caption font-mono text-ink-muted` — `caseNumber · {minutes} min` |
| Trailing | `<Badge variant="success">Completed</Badge>` |

### 6.26 Language Switcher (button group)

| Property | Value |
| --- | --- |
| Container | `hidden md:inline-flex items-center bg-surface-container rounded-md p-0.5` |
| Button | `h-8 px-2.5 rounded text-caption font-mono uppercase tracking-wide transition-colors` |
| Active | `bg-white text-ink shadow-soft` |
| Inactive | `text-ink-muted hover:text-ink` |
| A11y | `aria-label="{common.language}: {EN|UZ|RU}"` |

### 6.27 STT Language Picker (segmented control)

| Property | Value |
| --- | --- |
| Container | `flex rounded-md border border-outline-soft overflow-hidden` |
| Button | `px-3 py-1.5 text-caption font-medium transition-colors` |
| Active | `bg-primary-500 text-white` |
| Inactive | `bg-white text-ink hover:bg-surface-container-low` |
| Disabled (busy / recording) | `opacity-50 cursor-not-allowed` |

### 6.28 EmptyState

**Source:** `src/components/ui/EmptyState.tsx`.

| Property | Value |
| --- | --- |
| Container | `flex flex-col items-center justify-center text-center py-12 px-6 gap-3` |
| Icon container | `h-12 w-12 rounded-full bg-surface-container text-ink-muted inline-flex items-center justify-center mb-1` |
| Title | `text-title-lg text-ink` |
| Description | `text-body-md text-ink-muted max-w-sm` |
| Action | `mt-2` |

---

## 7. Iconography

### 7.1 Library
- **`lucide-react`** (v0.428). Tree-shake per import.
- Stroke: 2px (Lucide default), no fill unless explicitly used (e.g. `fill-current` for the Play/Square icons inside buttons).
- Optical sizing: keep the icon and the surrounding text aligned on the cap-height line; the wrapper cell sizes the icon, not the line.

### 7.2 Default Sizes

| Context | Size | Tailwind |
| --- | --- | --- |
| Inline with `text-caption` (12px) | 12px | `h-3 w-3` |
| Inline with `text-body-md` (14px) — table cell icon | 14px | `h-3.5 w-3.5` |
| Inline with `text-body-lg` (16px) — button `sm` | 16px | `h-4 w-4` |
| Button `md/lg`, table row avatar | 20px | `h-5 w-5` |
| Hero / card icon (`h-12 w-12` container) | 24px | `h-6 w-6` |
| Idle/Stopping hero icon | 28px | `h-7 w-7` |

### 7.3 Placement Rules
- Always wrap the icon in a sized container (`h-X w-X rounded-md|full bg-...`) when it is a category/visual marker (table cell avatar, stat-card icon, idle hero).
- When paired with a text label, place the icon to the left of the text; gap is `gap-1.5` (button `sm`) or `gap-2` (button `md`/`lg`).
- `shrink-0` is mandatory on icons inside flex rows that contain `truncate` text.

### 7.4 Spacing Rules
- Icon-only IconButton: centred, no extra padding inside the sized box.
- Table row icons: `mr-3` equivalent via parent `gap-3`.
- Pill / chip icons: `gap-1.5` between the dot/avatar and the label.

---

## 8. Shadows & Depth

### 8.1 Shadow Tokens

| Token | Value | Used On |
| --- | --- | --- |
| `shadow-soft` | `0 1px 2px 0 rgba(15, 23, 42, 0.04)` | Cards, language-switcher active button |
| `shadow-floating` | `0 4px 6px -1px rgba(15, 23, 42, 0.10), 0 2px 4px -2px rgba(15, 23, 42, 0.05)` | "↓ Latest" transcript scroll affordance, (reserved for modals) |

### 8.2 Elevation Philosophy
- **No shadow on the app shell, top bar, sidebar, or page wrapper.**
- **Cards carry one soft shadow only.** `shadow-soft` on `Card` (defined in the component).
- **Floating elements** (scroll affordance, future modals/menus) use `shadow-floating`.
- **No inner shadow, no coloured shadow, no glow.**
- Tonal layering (background → container-low → container → high) is preferred over shadow to express depth.

### 8.3 Border Philosophy
- Default border: 1px `outline-soft` (`#E2E8F0`).
- Active session banner overrides to `border-primary-200` and adds a soft tinted surface (`bg-primary-50/30`).
- Live session status bar uses 1px `red-200` (a non-tokenised Tailwind default, paired with `error-container`); keep both together to preserve contrast.
- Sidebar internal dividers use `border-white/5` (5% white on navy-700).

---

## 9. Motion System

The product uses **intentionally minimal motion**. Animation exists only where it conveys live state or feedback.

### 9.1 Durations

| Token | Value | Used For |
| --- | --- | --- |
| `duration-75` | 75ms | Audio meter bar fills |
| `duration-150` | 150ms | All Tailwind `transition-colors` (buttons, nav, inputs) |
| `1.4s` (`animate-pulse-dot`) | 1400ms | Live badge dot, speaking-indicator bars |
| `1.6s` (`animate-pulse-live`) | 1600ms | Reserved (live-pulse ring on container) |

### 9.2 Easing
- Default for `transition-colors`: Tailwind default (`cubic-bezier(0.4, 0, 0.2, 1)`).
- `animate-pulse-live`: `ease-in-out`.
- `animate-pulse-dot`: `ease-in-out`.

### 9.3 Animations Catalog

| Keyframe | Behaviour | Used By |
| --- | --- | --- |
| `pulseLive` | Box-shadow expands from `0 0 0 0 rgba(16,185,129,.5)` to `0 0 0 8px rgba(16,185,129,0)` | Reserved |
| `pulseDot` | Opacity `1` → `0.4` → `1` | Live badge dot, live-banner status dot, speaking-indicator bars |

### 9.4 Interaction Feedback
- **Hover:** `transition-colors duration-150` on every interactive surface (Button, IconButton, nav, table row, card-on-hover, language switcher).
- **Active/pressed:** No explicit transform; the pressed state is the deeper tonal step (`primary-700` for the primary button).
- **Focus:** `focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface`. The offset colour matches the page background.
- **No bouncy / spring motion.** No scale transforms on hover. No skeleton shimmer.

### 9.5 Modal / Drawer Motion
- **No modals in CP1.** When introduced, use a 150ms fade for the backdrop and a 150ms `translate-y-1 → translate-y-0` slide for the panel.

---

## 10. Responsive Rules

### 10.1 Breakpoint Cascade

| Range | Sidebar | Topbar | Page | Tables |
| --- | --- | --- | --- | --- |
| `< sm` (≤639) | hidden | search + help | `p-6` | first + last column only; horizontal scroll for the rest |
| `sm` (640–767) | hidden | + language switcher hidden, system pill hidden | `p-6` | + duration column (`hidden sm:table-cell`) |
| `md` (768–1023) | hidden | + system pill + language switcher | `p-8` | + started column (`hidden md:table-cell`) |
| `lg` (1024–1279) | **visible** | full | `p-8 max-w-screen-2xl` | + judge column (`hidden lg:table-cell`); transcript body becomes `1fr / 320px` |
| `xl / 2xl` (≥1280) | visible | full | `p-8 max-w-screen-2xl` | all columns |

### 10.2 Sidebar Transformation
- CP1: sidebar is **always present at lg, always hidden below lg**. There is no hamburger menu, no drawer, no bottom nav in CP1. Mobile users are routed to the same pages; the chrome collapses by hiding the sidebar.
- CP2: a `MobileShell` is reserved under `featureFlags.mobileShell` (currently `false`).

### 10.3 Page Header
- `flex-col` on mobile (title above actions), `flex-row md:items-center md:justify-between` from `md` up.
- The `mb-8` always applies.

### 10.4 Grid Collapse
- Subsystem row: `grid-cols-1 sm:grid-cols-3` — collapses to a single column on phones, expands to 3-up at `sm`.
- Cases summary tiles: `grid-cols-1 sm:grid-cols-2`.
- Live session body: `grid-cols-1 lg:grid-cols-[1fr_320px]` — stacks on phones, splits with a 320px right rail from `lg`.
- Active session banner: `flex-col md:flex-row` — stacks icon+text over elapsed+button on mobile.

### 10.5 Spacing Adjustments
- Page padding: `p-6` mobile, `p-8` desktop.
- Card padding: kept constant at 16 / 24 / 32 regardless of breakpoint (size variants are explicit props, not responsive).

---

## 11. Accessibility

### 11.1 Contrast
- `text-ink` (`#0B1C30`) on `bg-white` and `bg-surface` — far above WCAG AA for body text.
- `text-ink-muted` (`#464555`) on `bg-white` — passes AA for body text and large text.
- `text-white/70` on `bg-navy-700` (`#0F172A`) — passes AA for body text.
- `text-white/50` (sidebar tagline) on `bg-navy-700` — used only for non-essential small text (12px, 500 weight, uppercase); do not extend to body content.
- Primary button: white text on `primary-500` (`#4F46E5`) — passes AA at 14px+ weight 500.
- Live state: `text-error` (`#BA1A1A`) on `bg-error-container` (`#FFDAD6`) — passes AA.

### 11.2 Readable Sizing
- Minimum body size: 14px (`text-body-md`).
- Minimum caption / label size: 12px (`text-caption`, `text-label-md`) — used only for metadata.
- All numbers in tables, timers, durations use `tabular-nums` so digits align and remain scannable.

### 11.3 Touch Targets
- IconButton `sm` is 32×32 — used inside dense toolbars; acceptable for pointer but not the primary target.
- All Button sizes (32/40/48) meet or exceed 32px minimum.
- Sidebar nav items are 40px tall.
- Language switcher buttons are 32px tall — acceptable for secondary controls.

### 11.4 Keyboard Focus
- All interactive elements (Button, IconButton, Input, NavLink, segmented controls, language switcher) share a single focus ring: `focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface`.
- Disabled controls do not show the ring (browser default disabled handling).
- `IconButton` always requires a `label` prop that becomes `aria-label` and `title`.

### 11.5 Semantic Color Usage
- **Success / online / completed** → emerald scale (`emerald-500/600/100`).
- **Warning / degraded / in-hearing** → amber scale + primary text in `amber-700`.
- **Error / offline / live / danger** → `error` scale (`#BA1A1A` family).
- **Info** → primary indigo scale.
- **Neutral** → surface container + ink muted.
- Color is always paired with a textual label (badge text, status word) — colour is never the sole indicator.

### 11.6 Internationalisation
- i18n is wired up via `react-i18next` with three locales: `en`, `uz`, `ru`. Default is `en`; persisted in `localStorage` under `sud-lang`.
- All UI strings must come from the translation file; no English hard-coded copy in components beyond strings shown in the source for clarity (e.g. "LIVE" badge text — these are intentional brand/system labels).

---

## 12. Screen Map

The router is defined in `src/app/router.tsx`. CP1 ships three routes; CP2 routes are present in code but commented out and gated by `ENABLED_FEATURES` flags.

### 12.1 Route Inventory

| Path | Component | Feature flag | Purpose |
| --- | --- | --- | --- |
| `/` | `<Navigate to="/dashboard">` | always | Default redirect |
| `/dashboard` | `Dashboard` | `dashboard: true` | System health + active session banner + recent sessions table + Start Session CTA |
| `/cases` | `Cases` | `cases: true` | Case list with status, hearing date, judge, parties — read-only |
| `/sessions` | `Sessions` | `sessions: true` | Real-time transcription + speaker identification + STT control bar |
| `/dashboard` (default) | (n/a) | always | Unknown route redirects here |

### 12.2 Screen Specifications

#### Screen 1 — Dashboard (`/dashboard`)

- **Purpose:** Orient the operator: is the system healthy? Is there a live session? What happened recently?
- **Layout:** `p-6 md:p-8 max-w-screen-2xl`; single column.
- **Blocks (top → bottom):**
  1. **PageHeader** with title "Dashboard", subtitle "Overview of judicial sessions and system health", action `Start Session` button (primary, size `lg`, leftIcon `Play h-5 w-5 fill-current`).
  2. **System Status card** (`Card padding="lg"`) — top: 12×12 icon + title + status badge + subtitle. Body: 1/3-up subsystem grid.
  3. **Active Session banner** (conditional, only when a live session exists) — `Card padding="md" border-primary-200 bg-primary-50/30` with mic icon, title + live badge, case number mono, elapsed timer, "Open Session" button.
  4. **Recent Sessions card** — `Card padding="md"`, header with title "Recent Sessions" / subtitle "Today" and `View all` ghost button, then a `<table>`.
- **Interaction priority:** Start Session is the primary action. Status is the first thing the operator reads.

#### Screen 2 — Cases (`/cases`)

- **Purpose:** Show all cases, surface "in hearing now" cases, and let the operator jump to a session.
- **Layout:** `p-6 md:p-8 max-w-screen-2xl`; single column.
- **Blocks:**
  1. **PageHeader** with title "Cases", subtitle "All cases scheduled for hearing. Filters and analytics coming in Checkpoint 2.", action `New Case` secondary button (disabled in CP1).
  2. **Summary tiles** — 2-up grid: "Total cases" + "In hearing now", each `bg-white border border-outline-soft rounded-lg p-4 flex items-center gap-3` with 10×10 primary-50 icon container.
  3. **All Cases table** — `Card padding="md"` with header "All Cases" / "N records" and a `<table>`; row click navigates to `/sessions`.
- **Interaction priority:** Reading the table; rows are clickable but no detail page exists in CP1.

#### Screen 3 — Sessions (`/sessions`)

- **Purpose:** Run a live transcript + speaker identification session.
- **Layout:** `p-6 md:p-8 max-w-screen-2xl`; column.
- **State machine:** `idle → starting → live → stopping → idle`.
- **Blocks (idle):**
  1. **PageHeader** with title "Sessions", subtitle "Real-time transcription and speaker identification".
  2. **Idle view** — `Card padding="lg" text-center` with hero icon, "No active session", description, "Back to Dashboard" ghost button + "Start Session" lg primary button.
  3. **Control bar** (sticky bottom-4) — `Card padding="md"`: audio meter, mute, start.
  4. **Recent Sessions card** (top 3) — `Card padding="md"`.
  5. **Live STT test** — `Card padding="md"`, with language picker, mic/stop button, error/result blocks.
- **Blocks (live):**
  1. **PageHeader** — title "Sessions", subtitle = `caseNumber · judge`.
  2. **Live Session card** — `Card padding="none" overflow-hidden` with red status bar, transcript + speaker list.
  3. **Control bar** — sticky; Stop button replaces Start.
- **Interaction priority:** Start/Stop are the primary actions. The transcript auto-scrolls.

#### Screen 4 — Coming Soon (CP2 reserved)

- **Purpose:** Placeholder for any CP2 module.
- **Layout:** `p-6 md:p-8 max-w-2xl mx-auto`.
- **Blocks:** `Card padding="lg" text-center` with construction icon, "Coming in Checkpoint 2", description, "Dashboard" secondary button.

---

## 13. Design Tokens for Tailwind

The tokens below are a **direct copy** of `tailwind.config.ts` `theme.extend`. They are the implementation reference.

### 13.1 Colors

```ts
colors: {
  primary: { 50, 100, 200, 300, 400, 500, 600, 700, 800, 900 },
  navy:    { DEFAULT, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900 },
  emerald: { 50, 100, 200, 300, 400, 500, 600, 700 },
  surface: { DEFAULT, dim, bright,
             'container-lowest', 'container-low', 'container',
             'high', 'highest', 'variant' },
  ink:     { DEFAULT, muted, subtle },
  outline: { DEFAULT, variant, soft },
  error:   { DEFAULT, container, on, onContainer },
}
```

Use `bg-{name}-{step}` / `text-{name}-{step}` / `border-{name}-{step}` / `ring-{name}-{step}`.

For the speaker-role palette (§2.8), use Tailwind's default 50/500/700 ramps (no custom token needed).

### 13.2 Spacing

```ts
spacing: {
  '4.5': '1.125rem',  // 18px — sidebar nav icon-to-label
  'sidebar': '280px',
  'topbar':  '4rem',  // 64px
  'gutter':  '1.25rem' // 20px
}
```

Use as `w-sidebar`, `h-topbar`, `p-4.5`, `p-gutter`. The base 4px scale (`1`, `2`, `3`, ...) is unmodified.

### 13.3 Border Radius

```ts
borderRadius: {
  sm: '0.25rem',      // 4
  DEFAULT: '0.5rem',  // 8
  md: '0.75rem',      // 12
  lg: '1rem',         // 16
  xl: '1.5rem',       // 24
}
```

Use as `rounded`, `rounded-sm`, `rounded-md`, `rounded-lg`, `rounded-xl`. The base `rounded` and `rounded-lg` (8px) are the defaults; `rounded-md` is the input / button group default.

### 13.4 Box Shadow

```ts
boxShadow: {
  soft:     '0 1px 2px 0 rgba(15, 23, 42, 0.04)',
  floating: '0 4px 6px -1px rgba(15, 23, 42, 0.10), 0 2px 4px -2px rgba(15, 23, 42, 0.05)',
}
```

### 13.5 Font Family

```ts
fontFamily: {
  sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
  mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'monospace'],
}
```

### 13.6 Font Size

```ts
fontSize: {
  'display-lg':         ['3rem',    { lineHeight: '3.5rem', letterSpacing: '-0.02em', fontWeight: '700' }],
  'headline-lg':        ['2rem',    { lineHeight: '2.5rem', letterSpacing: '-0.01em', fontWeight: '600' }],
  'headline-lg-mobile': ['1.5rem',  { lineHeight: '2rem',   letterSpacing: '-0.01em', fontWeight: '600' }],
  'headline-md':        ['1.5rem',  { lineHeight: '2rem',   fontWeight: '600' }],
  'title-lg':           ['1.125rem',{ lineHeight: '1.75rem',fontWeight: '600' }],
  'body-lg':            ['1rem',    { lineHeight: '1.5rem', fontWeight: '400' }],
  'body-md':            ['0.875rem',{ lineHeight: '1.25rem',fontWeight: '400' }],
  'label-md':           ['0.75rem', { lineHeight: '1rem',   fontWeight: '500' }],
  'caption':            ['0.75rem', { lineHeight: '1rem',   fontWeight: '400' }],
}
```

### 13.7 Animation

```ts
animation: {
  'pulse-live': 'pulseLive 1.6s ease-in-out infinite',
  'pulse-dot':  'pulseDot 1.4s ease-in-out infinite',
}
keyframes: {
  pulseLive: { '0%,100%': { boxShadow: '0 0 0 0 rgba(16,185,129,.5)' },
               '50%':     { boxShadow: '0 0 0 8px rgba(16,185,129,0)' } },
  pulseDot:  { '0%,100%': { opacity: '1' }, '50%': { opacity: '0.4' } },
}
```

### 13.8 Container

```ts
container: {
  center: true,
  padding: { DEFAULT: '1rem', md: '2rem' },
}
```

### 13.9 Composite Utilities (defined in `globals.css`)

| Class | Effect |
| --- | --- |
| `text-mono` | `font-mono text-label-md tracking-wide uppercase` |
| `tabular-nums` | `font-variant-numeric: tabular-nums` |
| Body baseline | `bg-surface text-ink font-sans text-body-md` |

---

## 14. Implementation Rules

The following are **non-negotiable invariants** that define the visual identity. Multiple teams should treat them as merge-blocking.

### 14.1 What Must Stay Consistent
1. **No new hex values.** Use tokens. The full palette is §2; if a needed colour is not there, it is a design system bug — add a token, not an inline hex.
2. **The dark sidebar at `navy-700` with `text-white/70` inactive items is the visual signature.** Do not replace it with a light sidebar, do not change the active item rail to anything other than `primary-500` 2px.
3. **Every numeric / metadata field uses `font-mono` + `tabular-nums`.** Case numbers, durations, IDs, timestamps, system keys, language switcher labels.
4. **Every table column header uses `text-mono` (uppercase mono 12 ink-muted).** No exceptions, even for the first column.
5. **Cards always have the same chrome**: `bg-white border border-outline-soft rounded-lg shadow-soft`. The `padding` prop selects the inner padding, not the chrome.
6. **Focus rings are uniform**: `focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 focus-visible:ring-offset-surface`. The offset colour matches the page background.
7. **Buttons share the same focus ring, the same disabled handling, and the same `font-medium` weight.**
8. **Use `cn()` from `@/lib/cn` for all conditional class composition.** It is `twMerge(clsx(...))` and is the only sanctioned helper.
9. **All copy that is not a brand/system label must come from `i18n.ts`.** Add a new key, do not hardcode English.
10. **Animation policy is in §9.** If a new component needs motion, follow `duration-75` (audio meter) or `duration-150` (everything else), with `animate-pulse-dot` reserved for live indicators. Anything else is by design review.

### 14.2 What Should Never Be Changed
- The Tailwind `theme.extend` colour values, radii, shadows, font sizes, font families, or animation keyframes.
- The sidebar layout, width (`280px`), background (`navy-700`), or text colour palette.
- The topbar height (`64px`), padding, sticky positioning, or the system-status pill placement.
- The `Card` chrome (border, radius, shadow) and its `padding` variant values.
- The Button variants / sizes and their colour stops.
- The Badge variant palette and the dot animation.
- The transcript entry layout (accent dot, speaker pill, timestamp, body) and the auto-scroll threshold (`40` px from bottom).
- The live session status bar styling (`bg-error-container` + `border-red-200` + `text-mono text-error` "LIVE" + the dual pulsing dot).
- The audio meter 24-bar layout, band thresholds (16 / 21), and the `transition-all duration-75` cadence.
- The focus ring recipe (§11.4).

### 14.3 Visual Identity Anchors
The four elements that make the product *look like Sud-Tizimi* and not generic Bootstrap / Material / shadcn:

1. **The `navy-700` sidebar with a `primary-500` 2px active rail.**
2. **The mono-uppercase table headers and the mono-tabular numerics throughout the data layer.**
3. **The live transcript: a 2px coloured dot, a `style.bg / style.text` speaker pill, a `HH:MM:SS` mono timestamp, then 16px body in `text-ink`.**
4. **The audio meter — 24 vertical bars, emerald / amber / red banded, animated at 75ms — visible in the control bar.**

### 14.4 Multi-Team Consistency Workflow
- **Component reuse is mandatory.** If a UI primitive exists in `src/components/ui/`, use it. Do not reimplement `Button`, `Card`, `Badge`, `StatCard`, `IconButton`, or `EmptyState` with a one-off styling.
- **Layout shell is `AppShell` + `Sidebar` + `TopBar` + `PageHeader`.** Every page renders inside the `<Outlet/>` of `AppShell` and starts with `<PageHeader/>`. Do not invent a new shell.
- **Page wrapper is `p-6 md:p-8 max-w-screen-2xl`.** Use it as-is.
- **Token additions go through `tailwind.config.ts` + a PR to this document.** Do not extend the palette in a feature branch.
- **Adding a new colour, radius, shadow, or font size requires a design review** and a corresponding addition to §2 / §4 / §8 / §13.
- **All Lucide icons are imported from `lucide-react` and named in PascalCase.** No inline SVGs in CP1.
- **State colours:** success → emerald family, warning → amber family, error → `error` family, info → primary family, live → `error` family. Never repurpose.
- **The role palette (§2.8) is the only multi-colour mapping in the system.** Any new entity colour should follow the same pattern (50 / 500 / 700 ramp + role-keyed mapping in `lib/`).

### 14.5 Quick "Is this on-brand?" Checklist
- [ ] All colours come from tokens in §2.
- [ ] All sizes come from §3.2 or Tailwind defaults.
- [ ] No custom shadows beyond `shadow-soft` and `shadow-floating`.
- [ ] Border radius is `rounded` (4), `rounded-md` (6), `rounded-lg` (8), or `rounded-full` (pills only).
- [ ] Numerics are mono + tabular.
- [ ] Table headers are `text-mono` uppercase `text-ink-muted`.
- [ ] Card chrome is unchanged.
- [ ] No new icon libraries.
- [ ] All copy is i18n'd.
- [ ] Focus ring matches the recipe.
- [ ] Live state is conveyed by `animate-pulse-dot` + colour, never by an icon swap.
