import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { ThemeToggle } from "../src/components/ThemeToggle"

afterEach(() => cleanup())

describe("ThemeToggle", () => {
  it("默认亮色 → 显示月亮图标", () => {
    document.documentElement.setAttribute("data-theme", "light")
    render(<ThemeToggle />)
    expect(screen.getByText("🌙")).toBeTruthy()
  })

  it("点击切换为暗色 → 显示太阳图标", async () => {
    document.documentElement.setAttribute("data-theme", "light")
    const user = userEvent.setup()
    render(<ThemeToggle />)
    await user.click(screen.getByRole("button"))
    expect(document.documentElement.getAttribute("data-theme")).toBe("dark")
    expect(screen.getByText("☀️")).toBeTruthy()
  })

  it("再点击切回亮色", async () => {
    document.documentElement.setAttribute("data-theme", "dark")
    const user = userEvent.setup()
    render(<ThemeToggle />)
    await user.click(screen.getByRole("button"))
    expect(document.documentElement.getAttribute("data-theme")).toBe("light")
    expect(screen.getByText("🌙")).toBeTruthy()
  })
})