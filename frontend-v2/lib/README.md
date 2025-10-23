# Utility Functions

This directory contains utility functions used throughout the frontend application.

## utils.ts

The `utils.ts` file provides the `cn` utility function, which is the standard utility used by all shadcn/ui components.

### `cn` Function

Combines `clsx` (for conditional class composition) and `tailwind-merge` (for intelligent Tailwind CSS class merging).

```typescript
import { cn } from "@/lib/utils"

// Basic usage
const className = cn("text-base", "font-bold")

// Conditional classes
const className = cn("text-base", isActive && "text-blue-500")

// Merge conflicting Tailwind classes
const className = cn("px-4 py-2", "px-6") // Results in: "py-2 px-6"
```

### Dependencies

- **clsx** (^2.1.1): Utility for constructing className strings conditionally
- **tailwind-merge** (^3.3.1): Utility for merging Tailwind CSS classes without conflicts

Both dependencies are already included in the project's package.json.

### Usage in shadcn/ui Components

All shadcn/ui components use this utility to merge their base styles with user-provided className props:

```typescript
// Example from button.tsx
<button
  className={cn(buttonVariants({ variant, size }), className)}
  {...props}
/>
```

This allows users to override or extend component styles while ensuring Tailwind classes are properly merged without conflicts.
