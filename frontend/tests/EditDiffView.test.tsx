// @vitest-environment node
// parseEditCall 是纯函数，不需要 jsdom，同时绕开当前 jsdom+Node22 的 ESM 冲突
import { describe, it, expect } from "vitest"
import { parseEditCall } from "../src/components/EditDiffView"

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
