"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/lib/themes/theme-provider";
import { themes, ThemeName } from "@/lib/themes/theme-config";

export default function SettingsPage() {
  const { settings, updateSettings } = useTheme();

  const fontSizes = [
    { value: "sm", label: "Small", description: "14px" },
    { value: "base", label: "Default", description: "16px" },
    { value: "lg", label: "Large", description: "18px" },
    { value: "xl", label: "Extra Large", description: "20px" },
  ] as const;

  return (
    <div className="container max-w-4xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Customize your OpenGovt experience
        </p>
      </div>

      {/* Theme Selection */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>
            Choose your preferred color theme
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {Object.entries(themes).map(([key, theme]) => (
              <button
                key={key}
                onClick={() => updateSettings({ theme: key as ThemeName })}
                className={`p-4 rounded-lg border-2 transition-all ${
                  settings.theme === key
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/50"
                }`}
              >
                <div className="flex items-center gap-3 mb-2">
                  <div
                    className="w-8 h-8 rounded-full"
                    style={{
                      background: `hsl(${theme.colors.primary})`,
                    }}
                  />
                  <div className="text-left">
                    <div className="font-semibold">{theme.name}</div>
                  </div>
                </div>
                <div className="flex gap-1 mt-2">
                  {["primary", "secondary", "accent", "muted"].map((colorKey) => (
                    <div
                      key={colorKey}
                      className="flex-1 h-6 rounded"
                      style={{
                        background: `hsl(${
                          theme.colors[colorKey as keyof typeof theme.colors]
                        })`,
                      }}
                    />
                  ))}
                </div>
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Font Size */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Font Size</CardTitle>
          <CardDescription>
            Adjust text size for better readability
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {fontSizes.map((size) => (
              <Button
                key={size.value}
                variant={settings.fontSize === size.value ? "default" : "outline"}
                onClick={() => updateSettings({ fontSize: size.value })}
                className="flex flex-col h-auto py-4"
              >
                <span className="font-semibold">{size.label}</span>
                <span className="text-xs opacity-70">{size.description}</span>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Dark Mode */}
      <Card>
        <CardHeader>
          <CardTitle>Dark Mode</CardTitle>
          <CardDescription>
            Toggle dark mode for reduced eye strain
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between">
            <div className="text-sm">
              {settings.darkMode ? "Dark mode is enabled" : "Light mode is enabled"}
            </div>
            <Button
              variant={settings.darkMode ? "default" : "outline"}
              onClick={() => updateSettings({ darkMode: !settings.darkMode })}
            >
              {settings.darkMode ? "🌙 Dark" : "☀️ Light"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Preview */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Preview</CardTitle>
          <CardDescription>
            See how your settings look
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="p-4 bg-card border rounded-lg">
              <h3 className="text-xl font-semibold mb-2">Sample Heading</h3>
              <p className="text-muted-foreground mb-4">
                This is how your text will appear with the current settings. Lorem ipsum dolor sit amet, consectetur adipiscing elit.
              </p>
              <div className="flex gap-2">
                <Button>Primary Button</Button>
                <Button variant="outline">Secondary</Button>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Reset */}
      <div className="mt-6 flex justify-end">
        <Button
          variant="outline"
          onClick={() =>
            updateSettings({
              theme: "purple",
              fontSize: "base",
              darkMode: false,
            })
          }
        >
          Reset to Defaults
        </Button>
      </div>
    </div>
  );
}
