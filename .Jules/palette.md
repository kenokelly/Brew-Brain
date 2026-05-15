## 2026-05-07 - [Accessibility & Keyboard Navigation Polish]
**Learning:** Custom UI components (modals/sidebars) often overlook native browser expectations like the Escape key for closing. Icon-only buttons are high-risk for accessibility if labels are omitted.
**Action:** Always implement Escape key handling in modal-like components and ensure all Lucide-icon buttons have descriptive aria-labels.
## 2026-05-15 - Focus State Verification
**Learning:** Native  utility classes in Tailwind are effective for satisfying accessibility (a11y) expectations for keyboard navigation without introducing custom CSS, though ensuring 'outline-none' is paired alongside is critical to overriding browser defaults cleanly.
**Action:** Always include 'focus-visible:ring-2 focus-visible:ring-primary outline-none' explicitly on custom interactive elements (like icon-only buttons or link wrappers) to meet basic a11y requirements.
## 2026-05-15 - Focus State Verification
**Learning:** Native focus-visible utility classes in Tailwind are effective for satisfying accessibility (a11y) expectations for keyboard navigation without introducing custom CSS, though ensuring outline-none is paired alongside is critical to overriding browser defaults cleanly.
**Action:** Always include focus-visible:ring-2 focus-visible:ring-primary outline-none explicitly on custom interactive elements (like icon-only buttons or link wrappers) to meet basic a11y requirements.
