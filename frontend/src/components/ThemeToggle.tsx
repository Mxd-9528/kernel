import { useState } from "react"

const STORAGE_KEY = "theme"

function getTheme(): string {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored === "light" || stored === "dark") return stored
  return "light"
}

export function ThemeToggle() {
  const [theme, setTheme] = useState(getTheme)

  // 初始化时设置 data-theme
  if (typeof document !== "undefined" && document.documentElement.getAttribute("data-theme") !== theme) {
    document.documentElement.setAttribute("data-theme", theme)
  }

  const toggle = () => {
    const next = theme === "light" ? "dark" : "light"
    localStorage.setItem(STORAGE_KEY, next)
    document.documentElement.setAttribute("data-theme", next)
    setTheme(next)
  }

  return (
    <button onClick={toggle} className="theme-toggle" aria-label="切换主题">
      {theme === "light" ? "🌙" : "☀️"}
    </button>
  )
}