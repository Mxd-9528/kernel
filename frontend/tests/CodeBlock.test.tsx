import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { CodeBlock } from "../src/components/CodeBlock"

afterEach(() => cleanup())

describe("CodeBlock", () => {
  // 用 textContent 判断——refractor 高亮会把内容拆成 token span
  const bodyText = (c: HTMLElement) =>
    (c.querySelector(".code-block-body,.code-block-inline") as HTMLElement | null)?.textContent || ""
  const previewText = (c: HTMLElement) =>
    (c.querySelector(".code-block-preview") as HTMLElement | null)?.textContent || ""

  it("多行代码默认折叠，显示前几行预览", () => {
    const code = "line1\nline2\nline3\nline4\nline5"
    const { container } = render(<CodeBlock code={code} language="python" />)
    const preview = previewText(container)
    expect(preview).toContain("line1")
    expect(preview).toContain("line2")
    expect(preview).toContain("line3")
    expect(preview).not.toContain("line4")
    expect(preview).toContain("...")
  })

  it("不超 PREVIEW_LINES 行时不显示省略号", () => {
    const code = "a\nb\nc"
    const { container } = render(<CodeBlock code={code} language="python" />)
    expect(previewText(container)).not.toContain("...")
  })

  it("单行代码直接显示，不折叠", () => {
    // 未注册语言 → refractor 退化为纯文本
    render(<CodeBlock code="print(hello)" language="unknown-lang" />)
    expect(screen.getByText("print(hello)")).toBeTruthy()
  })

  it("单行代码带高亮时仍显示为 code-block-inline", () => {
    const { container } = render(<CodeBlock code="print(hello)" language="python" />)
    const inline = container.querySelector(".code-block-inline")
    expect(inline).toBeTruthy()
    expect(inline!.textContent).toBe("print(hello)")
  })

  it("空代码块直接显示", () => {
    render(<CodeBlock code="" language="python" />)
    expect(screen.queryByText("...")).toBeFalsy()
  })

  it("点击展开显示全部代码，再点击折叠", async () => {
    const user = userEvent.setup()
    const code = "a\nb\nc\nd\ne"
    const { container } = render(<CodeBlock code={code} language="python" />)
    // 折叠态：看不到 d
    expect(previewText(container)).not.toContain("d")
    // 点击展开
    await user.click(container.querySelector(".code-block")!)
    expect(bodyText(container)).toContain("d")
    expect(bodyText(container)).toContain("e")
    // 再点击折叠
    await user.click(container.querySelector(".code-block")!)
    expect(previewText(container)).not.toContain("d")
  })

  it("未注册语言参数不影响渲染（退化为纯文本）", () => {
    const code = "a\nb\nc\nd"
    render(<CodeBlock code={code} language="unknown-lang" />)
    expect(screen.queryByText("unknown-lang")).toBeFalsy()
  })
})