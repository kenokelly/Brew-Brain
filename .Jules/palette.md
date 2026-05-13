## 2026-05-07 - [Accessibility & Keyboard Navigation Polish]
**Learning:** Custom UI components (modals/sidebars) often overlook native browser expectations like the Escape key for closing. Icon-only buttons are high-risk for accessibility if labels are omitted.
**Action:** Always implement Escape key handling in modal-like components and ensure all Lucide-icon buttons have descriptive aria-labels.

## 2024-05-18 - [Simulation Grain Trash Button]
**Learning:** Found a bare trash icon button inside the `Simulation.tsx` that lacked `aria-label`, `title`, and explicit keyboard `focus-visible` styling, making it inaccessible for screen readers or keyboard navigation.
**Action:** Appended `aria-label` and `title` to the icon-only `<button>`, alongside applying `focus-visible:ring-2 focus-visible:outline-none focus-visible:ring-red-500` specifically tailored for the trash color theme.
