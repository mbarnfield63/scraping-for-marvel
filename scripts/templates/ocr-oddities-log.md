# OCR oddities log (one-offs)

Running log of **single**, paper-specific OCR garbles seen during extraction.
Each is a one-off so far. If the same form shows up in another paper, promote it
to a general rule in `scraper_template.md` (RECURRING OCR / TABLE HAZARDS).

Recurring patterns already promoted to the brief are NOT repeated here.

| First seen | Form | Example (raw → true) | How resolved | Times seen |
|------------|------|----------------------|--------------|------------|
| 74MaSa | Stray decimal point inserted into a wavenumber | `2.61.7211` → `2161.7211` | Two dots ⇒ malformed; true value obvious from branch position (R(3)≈2161.7) + blended flag | 1 |
| 74MaSa | Interior decimal digit read as a letter | `2128.7c62` → `2128.7262` | `c`→`2`, pinned by obs-calc (−0.0007) + neighbours P(98)=2129.10, P(100)=2128.34 | 1 |
