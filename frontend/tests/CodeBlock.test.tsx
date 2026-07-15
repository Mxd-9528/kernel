import { describe, it, expect, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { CodeBlock } from "../src/components/CodeBlock"

afterEach(() => cleanup())

describe("CodeBlock", () => {
  it("多行代码默认折叠，显示前几行预览", () => {
    const code = "line1\nline2\nline3\nline4\nline5"
    render(<CodeBlock code={code} language="python" />)
    // 折叠态：能看到前 3 行
    expect(screen.getByText(/line1/)).toBeTruthy()
    expect(screen.getByText(/line2/)).toBeTruthy()
    expect(screen.getByText(/line3/)).toBeTruthy()
    // 第 4 行不可见
    expect(screen.queryByText("line4")).toBeFalsy()
    // 显示省略号
    expect(screen.getByText(/\.\.\./)).toBeTruthy()
  })

  it("不超 PREVIEW_LINES 行时不显示省略号", () => {
    const code = "a\nb\nc"
    render(<CodeBlock code={code} language="python" />)
    expect(screen.queryByText(/\.\.\./)).toBeFalsy()
  })

  it("单行代码直接显示，不折叠", () => {
    render(<CodeBlock code="print('hello')" language="python" />)
    expect(screen.getByText("print('hello')")).toBeTruthy()
  })

  it("空代码块直接显示", () => {
    render(<CodeBlock code="" language="python" />)
    expect(screen.queryByText("...")).toBeFalsy()
  })

  it("点击展开显示全部代码，再点击折叠", async () => {
    const user = userEvent.setup()
    const code = "a\nb\nc\nd\ne"
    render(<CodeBlock code={code} language="python" />)
    // 折叠态
    expect(screen.queryByText("d")).toBeFalsy()
    // 点击展开
    await user.click(screen.getByText(/a/))
    expect(screen.getByText(/d/)).toBeTruthy()
    expect(screen.getByText(/e/)).toBeTruthy()
    // 再点击折叠
    await user.click(screen.getByText(/a/))
    expect(screen.queryByText("d")).toBeFalsy()
  })

  it("语言参数不影响渲染", () => {
    const code = "a\nb\nc\nd"
    render(<CodeBlock code={code} language="sql" />)
    expect(screen.queryByText("sql")).toBeFalsy()
  })
})