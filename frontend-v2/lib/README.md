# Utility Functions for shadcn/ui Components

## Overview

This directory contains utility functions used by shadcn/ui components throughout the frontend-v2 application.

## Files

### `utils.ts`

Contains the `cn` utility function for combining CSS class names.

**Purpose**: The `cn` function is a helper that combines multiple class names and handles conditional classes. It uses:
- `clsx` for conditional class name composition
- `tailwind-merge` for intelligently merging Tailwind CSS classes

**Usage**:

```typescript
import { cn } from "@/lib/utils"

// Basic usage
const className = cn("base-class", "another-class")
// Result: "base-class another-class"

// Conditional classes
const className = cn(
  "base-class",
  isActive && "active-class",
  { "hover-class": isHovering }
)

// Tailwind merge (prevents conflicts)
const className = cn("px-2 py-1", "px-4")
// Result: "py-1 px-4" (px-4 overrides px-2)
```

**Why this is needed**: All shadcn/ui components (Button, Card, Avatar, etc.) use this utility to:
1. Merge base component styles with user-provided className props
2. Handle conditional styling
3. Prevent Tailwind class conflicts

## Dependencies

- `clsx` (v2.1.1) - For composing class names conditionally
- `tailwind-merge` (v3.3.1) - For merging Tailwind CSS classes intelligently

These are already included in `package.json`.

## Path Alias

The `@/lib/utils` import is resolved via the TypeScript path mapping in `tsconfig.json`:

```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

This means `@/lib/utils` resolves to `/home/runner/work/opengovt/opengovt/frontend-v2/lib/utils.ts`.
