import { describe, it, expect, vi, beforeAll, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MessageBubble } from "../src/components/MessageBubble"

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})
afterEach(() => cleanup())

describe("MessageBubble", () => {
  it("user 消息显示内容", () => {
    render(<MessageBubble message={{ id: "1", role: "user", content: "你好" }} />)
    expect(screen.getByText("你好")).toBeTruthy()
  })

  it("assistant 消息渲染 markdown", () => {
    render(<MessageBubble message={{ id: "2", role: "assistant", content: "**加粗** `code` [链接](https://a.com)" }} />)
    const strong = document.querySelector("strong")
    expect(strong?.textContent).toBe("加粗")
    const code = document.querySelector("code.md-inline-code")
    expect(code?.textContent).toBe("code")
    const link = document.querySelector("a")
    expect(link?.getAttribute("href")).toBe("https://a.com")
  })

  it("assistant 消息渲染标题", () => {
    render(<MessageBubble message={{ id: "3", role: "assistant", content: "# 标题" }} />)
    const h1 = document.querySelector("h1")
    expect(h1?.textContent).toBe("标题")
  })

  it("assistant 消息渲染表格", () => {
    render(<MessageBubble message={{ id: "4", role: "assistant", content: "| a | b |\n|---|---|\n| 1 | 2 |" }} />)
    expect(document.querySelector("table")).toBeTruthy()
    expect(screen.getByText("1")).toBeTruthy()
  })

  it("assistant 消息渲染数学公式", () => {
    render(<MessageBubble message={{ id: "math", role: "assistant", content: "行内 $a^2+b^2=c^2$ 与块级 $$E=mc^2$$" }} />)
    // KaTeX 用 .katex 类包裹每个公式；行内 + 块级 = 至少 2 个
    const katex = document.querySelectorAll(".katex")
    expect(katex.length).toBeGreaterThanOrEqual(2)
  })

  it("assistant 讲解代码块渲染为 md-code-block，不带折叠 class", () => {
    render(<MessageBubble message={{ id: "5", role: "assistant", content: "```python\nprint('hi')\nprint('there')\n```" }} />)
    const block = document.querySelector(".md-code-block")
    expect(block).toBeTruthy()
    expect(block!.textContent).toContain("print('hi')")
    // 讲解代码块不复用折叠专用的 .code-block
    expect(document.querySelector(".code-block")).toBeNull()
  })

  it("assistant EXEC 段渲染为 .code-block（可折叠）", () => {
    render(<MessageBubble message={{ id: "6", role: "assistant", content: "前\n<EXEC>\n```python\nprint(1)\nprint(2)\nprint(3)\nprint(4)\n```\n</EXEC>\n后" }} />)
    expect(document.querySelector(".code-block")).toBeTruthy()
    // 讲解型不应出现
    expect(document.querySelector(".md-code-block")).toBeNull()
  })

  it("thinking 消息默认折叠，点击展开", async () => {
    const user = userEvent.setup()
    render(<MessageBubble message={{ id: "6", role: "thinking", content: "思考内容" }} />)
    // 折叠态
    expect(screen.getByText(/思考过程/)).toBeTruthy()
    expect(screen.queryByText("思考内容")).toBeFalsy()
    // 点击展开
    await user.click(screen.getByText(/思考过程/))
    expect(screen.getByText("思考内容")).toBeTruthy()
    // 再点击折叠
    await user.click(screen.getByText(/思考过程/))
    expect(screen.queryByText("思考内容")).toBeFalsy()
  })

  it("system 消息显示内容", () => {
    render(<MessageBubble message={{ id: "7", role: "system", content: "命令已执行" }} />)
    expect(screen.getByText("命令已执行")).toBeTruthy()
  })
})