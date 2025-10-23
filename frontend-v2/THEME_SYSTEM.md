# Theme System Documentation

## Overview

The OpenGovt frontend features a comprehensive, centralized theme management system that allows users to customize their experience with multiple color schemes, font sizes, and dark mode.

## Features

### 🎨 Multiple Theme Presets

**Purple Ocean (Default)**
- Rich purple color scheme matching our octopus mascot
- Warm, inviting, professional appearance
- Perfect for extended reading sessions

**Professional Blue**
- Facebook-inspired blue design
- Clean, familiar interface
- Business-appropriate aesthetic

**Dark Ocean**
- Easy on the eyes for night browsing
- Purple-tinted dark mode
- Reduces eye strain

### 🔤 Font Size Customization

Users can choose from 4 font sizes:
- **Small** (14px) - Compact display
- **Default** (16px) - Standard reading
- **Large** (18px) - Enhanced readability
- **Extra Large** (20px) - Maximum accessibility

### 🌓 Dark Mode

Toggle between light and dark modes for comfortable viewing in any environment.

### 🐙 Octopus Mascot - Octo

Interactive chat assistant that helps users:
- Navigate the platform
- Understand voting records
- Learn about analytics and metrics
- Customize their settings
- Get answers to common questions

**Features:**
- Floating button in bottom-right corner
- Click to open chat window
- Animated entrance
- Contextual help based on keywords
- Friendly, conversational interface

## Architecture

### File Structure

```
frontend-v2/
├── lib/
│   └── themes/
│       ├── theme-config.ts       # Theme definitions
│       └── theme-provider.tsx    # React context provider
├── components/
│   └── mascot/
│       └── octopus-mascot.tsx    # Interactive mascot component
├── app/
│   ├── layout.tsx                # Root layout with ThemeProvider
│   ├── globals.css               # Global styles with CSS variables
│   └── settings/
│       └── page.tsx              # Settings customization page
```

### Theme Configuration (theme-config.ts)

**Theme Interface:**
```typescript
interface Theme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    background: string;
    foreground: string;
    // ... and more
    democrat: string;
    republican: string;
    independent: string;
  };
  fonts: {
    sans: string;
    mono: string;
    display: string;
  };
  radius: string;
}
```

**Available Themes:**
- `purpleTheme` - Default purple ocean theme
- `blueTheme` - Professional blue theme
- `darkTheme` - Dark ocean theme

**Functions:**
- `applyTheme(theme: Theme)` - Applies theme to document
- `getTheme(name: ThemeName)` - Gets theme by name

### Theme Provider (theme-provider.tsx)

**React Context Provider** that:
- Loads saved settings from localStorage
- Applies theme on mount and when settings change
- Provides `useTheme()` hook for components
- Manages font size and dark mode state

**User Settings Interface:**
```typescript
interface UserSettings {
  theme: ThemeName;
  fontSize: "sm" | "base" | "lg" | "xl";
  darkMode: boolean;
}
```

**Hook Usage:**
```typescript
const { settings, updateSettings, currentTheme } = useTheme();
```

### Global Styles (globals.css)

CSS variables are defined at the `:root` level and dynamically updated by the theme system:

```css
:root {
  --primary: 262 83% 58%;
  --background: 0 0% 100%;
  --foreground: 262 83% 15%;
  /* ... */
  --democrat: 220 100% 45%;
  --republican: 0 87% 55%;
  --independent: 280 80% 50%;
}
```

Variables use HSL color space for easy manipulation.

## Usage

### Using the Theme Provider

In your component:

```typescript
import { useTheme } from "@/lib/themes/theme-provider";

function MyComponent() {
  const { settings, updateSettings, currentTheme } = useTheme();
  
  // Change theme
  updateSettings({ theme: "dark" });
  
  // Change font size
  updateSettings({ fontSize: "lg" });
  
  // Toggle dark mode
  updateSettings({ darkMode: !settings.darkMode });
  
  // Access current theme colors
  console.log(currentTheme.colors.primary);
}
```

### Using Theme Colors in Components

**With Tailwind:**
```tsx
<div className="bg-primary text-primary-foreground">
  Primary colored element
</div>

<div className="bg-democrat text-white">
  Democrat color
</div>
```

**With Inline Styles:**
```tsx
<div style={{ background: `hsl(var(--primary))` }}>
  Inline primary color
</div>
```

### Settings Page

Navigate to `/settings` to access the customization interface:
- Theme selection with visual previews
- Font size adjustment buttons
- Dark mode toggle
- Live preview of changes
- Reset to defaults button

## Adding New Themes

To add a new theme:

1. Define the theme in `theme-config.ts`:

```typescript
export const myNewTheme: Theme = {
  name: "My New Theme",
  colors: {
    primary: "180 80% 50%",
    // ... define all required colors
  },
  fonts: {
    sans: "'Arial', sans-serif",
    mono: "'Courier', monospace",
    display: "'Georgia', serif",
  },
  radius: "0.5rem",
};
```

2. Add to themes export:

```typescript
export const themes = {
  purple: purpleTheme,
  blue: blueTheme,
  dark: darkTheme,
  mynew: myNewTheme,  // Add here
};
```

3. The theme will automatically appear in Settings!

## Customizing the Octopus Mascot

The mascot's knowledge base is in `octopus-mascot.tsx`:

```typescript
const octopusKnowledge = {
  greeting: "Hi! I'm Octo...",
  topics: {
    "keyword": "Response text",
    // Add more topics
  }
};
```

To add new responses:
1. Add keywords to `topics` object
2. Add response patterns in `getOctopusResponse()` function
3. Update default responses array

## Best Practices

### Theme Design
- Use consistent color relationships (primary, secondary, accent)
- Ensure sufficient contrast for accessibility
- Test with both light and dark modes
- Consider political colors (Democrat blue, Republican red, Independent purple)

### Performance
- Theme changes apply immediately via CSS variables
- Settings persist in localStorage
- No page reload required
- Minimal performance impact

### Accessibility
- All themes meet WCAG color contrast requirements
- Font size options improve readability
- Dark mode reduces eye strain
- Semantic HTML with proper ARIA labels

## Future Enhancements

Potential additions to the theme system:

- [ ] More theme presets (Green, Orange, Neutral)
- [ ] Custom theme builder (user-defined colors)
- [ ] High contrast mode for accessibility
- [ ] Dyslexia-friendly font option
- [ ] Compact vs. comfortable spacing
- [ ] Animation preferences (reduced motion)
- [ ] Theme sharing (export/import)
- [ ] Per-profile themes
- [ ] Time-based theme switching (auto dark mode at night)

## Troubleshooting

**Theme not applying:**
- Check that ThemeProvider wraps your app in layout.tsx
- Verify CSS variables are defined in globals.css
- Clear localStorage if seeing old theme

**Colors look wrong:**
- Ensure using HSL format: `"hue saturation% lightness%"`
- Check that all required color variables are defined
- Verify dark mode class is toggled correctly

**Settings not persisting:**
- Check browser allows localStorage
- Verify no errors in console
- Try clearing localStorage and settings again

## API Reference

### useTheme Hook

```typescript
const {
  settings,        // Current user settings
  updateSettings,  // Function to update settings
  currentTheme,    // Active theme object
} = useTheme();
```

### Theme Functions

```typescript
applyTheme(theme: Theme): void
getTheme(name: ThemeName): Theme
```

### Types

```typescript
type ThemeName = "purple" | "blue" | "dark";
type FontSize = "sm" | "base" | "lg" | "xl";
```

---

For questions or contributions to the theme system, see the main repository documentation.
