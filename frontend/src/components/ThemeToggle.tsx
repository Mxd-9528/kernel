import { useState } from "react"

export function ThemeToggle() {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute("data-theme") ?? "light",
  )

  const toggle = () => {
    const next = theme === "light" ? "dark" : "light"
    document.documentElement.setAttribute("data-theme", next)
    setTheme(next)
  }

  return (
    <button onClick={toggle} className="theme-toggle" aria-label="切换主题">
      {theme === "light" ? "🌙" : "☀️"}
    </button>
  )
}