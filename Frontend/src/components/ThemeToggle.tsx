import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ThemeToggleProps {
  variant?: "default" | "compact";
  className?: string;
}

const ThemeToggle = ({ variant = "default", className }: ThemeToggleProps) => {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return null;
  }

  const isDark = theme === "dark";

  if (variant === "compact") {
    return (
      <button
        onClick={() => setTheme(isDark ? "light" : "dark")}
        className={cn(
          "inline-flex items-center rounded-full px-1 py-0.5 border border-border cursor-pointer transition-colors",
          isDark 
            ? "bg-neutral-800 dark:bg-neutral-800" 
            : "bg-neutral-200 dark:bg-neutral-200",
          className
        )}
        aria-label="Toggle theme"
      >
        <span
          className={cn(
            "text-[0.65rem] px-2 py-0.5 rounded-full transition-all",
            isDark
              ? "text-neutral-500"
              : "bg-white text-neutral-900 shadow-xs"
          )}
        >
          OFF
        </span>
        <span
          className={cn(
            "text-[0.65rem] px-2 py-0.5 rounded-full transition-all",
            isDark
              ? "bg-white text-neutral-900 shadow-xs"
              : "text-neutral-500"
          )}
        >
          ON
        </span>
      </button>
    );
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={cn("relative", className)}
      aria-label="Toggle theme"
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
      <span className="sr-only">Toggle theme</span>
    </Button>
  );
};

export default ThemeToggle;

