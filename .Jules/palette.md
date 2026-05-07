## 2026-05-07 - [Accessibility & Keyboard Navigation Polish]
**Learning:** Custom UI components (modals/sidebars) often overlook native browser expectations like the Escape key for closing. Icon-only buttons are high-risk for accessibility if labels are omitted.
**Action:** Always implement Escape key handling in modal-like components and ensure all Lucide-icon buttons have descriptive aria-labels.
