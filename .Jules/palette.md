## 2026-05-07 - [Accessibility & Keyboard Navigation Polish]
**Learning:** Custom UI components (modals/sidebars) often overlook native browser expectations like the Escape key for closing. Icon-only buttons are high-risk for accessibility if labels are omitted.
**Action:** Always implement Escape key handling in modal-like components and ensure all Lucide-icon buttons have descriptive aria-labels.

## 2026-05-10 - Icon-Only Button Accessibility Pattern
**Learning:** Found a recurring pattern across the app (e.g., Settings, Tap List) where icon-only buttons lack essential accessibility attributes like `aria-label` and `title`, as well as visual focus indicators (`focus-visible`) for keyboard navigation.
**Action:** Proactively scan for `<button>` elements containing only icons during code reviews and ensure they always have descriptive `aria-label`/`title` and proper keyboard focus states.
