## 2026-05-07 - [Accessibility & Keyboard Navigation Polish]
**Learning:** Custom UI components (modals/sidebars) often overlook native browser expectations like the Escape key for closing. Icon-only buttons are high-risk for accessibility if labels are omitted.
**Action:** Always implement Escape key handling in modal-like components and ensure all Lucide-icon buttons have descriptive aria-labels.
## 2024-05-11 - Refresh Interaction Consistency
**Learning:** In the TapList page, fetching data asynchronously without visual feedback or disabled states allowed rapid click-spamming, potentially overloading the API and causing confusing UI states. Icon-only utility buttons must combine both accessibility attributes (`aria-label`, `title`) and stateful loading indicators (`isRefreshing` triggering an `animate-spin` icon).
**Action:** When adding refresh or fetch-triggering icon buttons in Next.js/React components, always implement a dual-purpose pattern: provide an `aria-label`/`title` for screen readers, and bind a boolean `loading` or `isRefreshing` state to both the button's `disabled` property and an `animate-spin` class on the icon itself.
