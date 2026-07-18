import { describe, it, expect, afterEach } from "vitest"
import { render, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { parseEditCall, EditDiffView } from "../src/components/EditDiffView"

afterEach(() => cleanup())

describe("parseEditCall", () => {
  it("识别裸 edit() 调用", () => {
    const code = `edit("foo.py", "old", "new")`
    const diff = parseEditCall(code)
    expect(diff).not.toBeNull()
    expect(diff!.filePath).toBe("foo.py")
    expect(diff!.oldCode).toBe("old")
    expect(diff!.newCode).toBe("new")
  })

  it("首行是注释也能识别（回归：分栏对比原本失效）", () => {
    const code = `# 修改配置
edit("foo.py", "old", "new")`
    const diff = parseEditCall(code)
    expect(diff).not.toBeNull()
    expect(diff!.filePath).toBe("foo.py")
    expect(diff!.oldCode).toBe("old")
    expect(diff!.newCode).toBe("new")
  })

  it("支持多行 old/new 代码", () => {
    const code = `edit("bar.py", "line1\nline2", "new1\nnew2\nnew3")`
    const diff = parseEditCall(code)
    expect(diff).not.toBeNull()
    expect(diff!.oldCode).toBe("line1\nline2")
    expect(diff!.newCode).toBe("new1\nnew2\nnew3")
  })

  it("非 edit 代码返回 null", () => {
    expect(parseEditCall(`print("hello")`)).toBeNull()
    expect(parseEditCall(`# 一段注释\nx = 1`)).toBeNull()
    expect(parseEditCall(``)).toBeNull()
  })

  it("edit 参数不足返回 null", () => {
    expect(parseEditCall(`edit("foo.py")`)).toBeNull()
    expect(parseEditCall(`edit("foo.py", "old")`)).toBeNull()
  })
})

describe("EditDiffView 视觉 diff", () => {
  const diff = { filePath: "x.py", oldCode: "a\nb\nc", newCode: "a\nB\nc" }
  const code = `edit("x.py", "a\\nb\\nc", "a\\nB\\nc")`

  it("折叠态点击展开出现双栏容器", async () => {
    const user = userEvent.setup()
    const { container } = render(<EditDiffView code={code} diff={diff} />)
    expect(container.querySelector(".edit-diff-split")).toBeNull()
    await user.click(container.querySelector(".code-block")!)
    expect(container.querySelector(".edit-diff-split")).toBeTruthy()
  })

  it("修改行两栏对齐，未变化行不带 edit-line-* class", async () => {
    const user = userEvent.setup()
    const { container } = render(<EditDiffView code={code} diff={diff} />)
    await user.click(container.querySelector(".code-block")!)
    const oldLines = container.querySelectorAll(".edit-diff-old div")
    const newLines = container.querySelectorAll(".edit-diff-new div")
    expect(oldLines.length).toBe(newLines.length)
    // a 与 c 未变化
    expect(oldLines[0].className).toBe("")
    expect(newLines[0].className).toBe("")
    // 中间 b→B 变化
    expect(oldLines[1].className).toContain("edit-line-del")
    expect(newLines[1].className).toContain("edit-line-add")
  })

  it("纯新增：左栏空行标 del、右栏新行标 add", async () => {
    const user = userEvent.setup()
    const d = { filePath: "x.py", oldCode: "", newCode: "new1\nnew2" }
    const c = `edit("x.py", "", "new1\\nnew2")`
    const { container } = render(<EditDiffView code={c} diff={d} />)
    await user.click(container.querySelector(".code-block")!)
    const newLines = container.querySelectorAll(".edit-diff-new div")
    // 至少两行新增
    const addCount = Array.from(newLines).filter(el => el.className.includes("edit-line-add")).length
    expect(addCount).toBeGreaterThanOrEqual(2)
  })

  it("纯删除：左栏所有非空行标 del", async () => {
    const user = userEvent.setup()
    const d = { filePath: "x.py", oldCode: "old1\nold2", newCode: "" }
    const c = `edit("x.py", "old1\\nold2", "")`
    const { container } = render(<EditDiffView code={c} diff={d} />)
    await user.click(container.querySelector(".code-block")!)
    const oldLines = container.querySelectorAll(".edit-diff-old div")
    const delCount = Array.from(oldLines).filter(el => el.className.includes("edit-line-del")).length
    expect(delCount).toBeGreaterThanOrEqual(2)
  })

  it("展开/折叠可来回切换", async () => {
    const user = userEvent.setup()
    const { container } = render(<EditDiffView code={code} diff={diff} />)
    const block = container.querySelector(".code-block")!
    await user.click(block)
    expect(container.querySelector(".edit-diff-split")).toBeTruthy()
    await user.click(block)
    expect(container.querySelector(".edit-diff-split")).toBeNull()
  })
})

describe("EditDiffView 词级高亮", () => {
  it("同一行内只改一个词时，未变化片段不带 edit-word-* class", async () => {
    const user = userEvent.setup()
    const d = { filePath: "x.py", oldCode: "foo = 1", newCode: "bar = 1" }
    const c = `edit("x.py", "foo = 1", "bar = 1")`
    const { container } = render(<EditDiffView code={c} diff={d} />)
    await user.click(container.querySelector(".code-block")!)
    // 修改行内应存在 edit-word-del / edit-word-add span
    expect(container.querySelector(".edit-word-del")).toBeTruthy()
    expect(container.querySelector(".edit-word-add")).toBeTruthy()
    // 且必然还有未变化的中性 span（"= 1" 部分）
    const oldRow = container.querySelector(".edit-diff-old .edit-line-del")!
    const neutralSpans = Array.from(oldRow.querySelectorAll("span")).filter(
      s => !s.className.includes("edit-word-")
    )
    expect(neutralSpans.length).toBeGreaterThan(0)
  })

  it("整行内容完全不同：几乎全部片段被标 add/del", async () => {
    const user = userEvent.setup()
    const d = { filePath: "x.py", oldCode: "aaa", newCode: "bbb" }
    const c = `edit("x.py", "aaa", "bbb")`
    const { container } = render(<EditDiffView code={c} diff={d} />)
    await user.click(container.querySelector(".code-block")!)
    expect(container.querySelector(".edit-word-del")).toBeTruthy()
    expect(container.querySelector(".edit-word-add")).toBeTruthy()
  })
})
