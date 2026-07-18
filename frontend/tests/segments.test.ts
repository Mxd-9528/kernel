import { describe, it, expect } from "vitest"
import { splitByExec, visiblePrefix, hasPendingExec } from "../src/lib/segments"

describe("visiblePrefix - 打字机穿过 <EXEC> 标签", () => {
  // 逐字符推进时，标签字符不应漏出
  it("末尾 '<' 被隐藏", () => {
    expect(visiblePrefix("你好<")).toBe("你好")
  })
  it("末尾 '<E' 被隐藏", () => {
    expect(visiblePrefix("你好<E")).toBe("你好")
  })
  it("末尾 '<EXEC' 被隐藏", () => {
    expect(visiblePrefix("你好<EXEC")).toBe("你好")
  })
  it("完整 <EXEC> 后不带任何字符时，未闭合段被隐藏，前缀保留", () => {
    expect(visiblePrefix("你好<EXEC>")).toBe("你好")
  })
  it("孤立 '<' 或 '<X' 不被误伤（不是 <EXEC 的前缀）", () => {
    expect(visiblePrefix("a<b")).toBe("a<b")
    expect(visiblePrefix("a<Xb")).toBe("a<Xb")
  })
})

describe("splitByExec", () => {
  it("空字符串 → []", () => {
    expect(splitByExec("")).toEqual([])
  })

  it("纯文本 → 单个 text 段", () => {
    expect(splitByExec("hello")).toEqual([{ type: "text", content: "hello" }])
  })

  it("完整 EXEC → text + exec(closed) + text", () => {
    const r = splitByExec("前\n<EXEC>\n```py\nx=1\n```\n</EXEC>\n后")
    expect(r).toEqual([
      { type: "text", content: "前\n" },
      { type: "exec", content: "\n```py\nx=1\n```\n", closed: true },
      { type: "text", content: "\n后" },
    ])
  })

  it("未闭合 EXEC → 末尾段 closed=false", () => {
    const r = splitByExec("前\n<EXEC>\n```py\nx=")
    expect(r).toEqual([
      { type: "text", content: "前\n" },
      { type: "exec", content: "\n```py\nx=", closed: false },
    ])
  })

  it("只有 <EXEC>", () => {
    expect(splitByExec("<EXEC>")).toEqual([
      { type: "exec", content: "", closed: false },
    ])
  })

  it("连续两个 EXEC 段", () => {
    const r = splitByExec("<EXEC>a</EXEC><EXEC>b</EXEC>")
    expect(r).toEqual([
      { type: "exec", content: "a", closed: true },
      { type: "exec", content: "b", closed: true },
    ])
  })

  it("EXEC 之间有文本", () => {
    const r = splitByExec("<EXEC>a</EXEC>中<EXEC>b</EXEC>")
    expect(r).toEqual([
      { type: "exec", content: "a", closed: true },
      { type: "text", content: "中" },
      { type: "exec", content: "b", closed: true },
    ])
  })

  it("拼接不变式：所有 content 相加 = 原文去标签", () => {
    const input = "前<EXEC>代码1</EXEC>中<EXEC>代码2</EXEC>后"
    const segs = splitByExec(input)
    const rebuilt = segs.map((s) => s.content).join("")
    const stripped = input.replace(/<\/?EXEC>/g, "")
    expect(rebuilt).toBe(stripped)
  })
})

describe("visiblePrefix", () => {
  it("纯文本 → 原样", () => {
    expect(visiblePrefix("hello")).toBe("hello")
  })

  it("含未闭合 EXEC → 只返回之前的文本", () => {
    expect(visiblePrefix("前\n<EXEC>\n```py\nx=")).toBe("前\n")
  })

  it("含已闭合 EXEC → 保留标签与内容", () => {
    expect(visiblePrefix("前<EXEC>a</EXEC>后")).toBe("前<EXEC>a</EXEC>后")
  })

  it("已闭合 + 未闭合 → 保留前者，切掉后者", () => {
    expect(visiblePrefix("前<EXEC>a</EXEC>中<EXEC>b=")).toBe("前<EXEC>a</EXEC>中")
  })
})

describe("hasPendingExec", () => {
  it("无 EXEC → false", () => {
    expect(hasPendingExec("hello")).toBe(false)
  })

  it("闭合 EXEC → false", () => {
    expect(hasPendingExec("<EXEC>a</EXEC>")).toBe(false)
  })

  it("未闭合 EXEC → true", () => {
    expect(hasPendingExec("<EXEC>a")).toBe(true)
  })

  it("闭合 + 未闭合 → true", () => {
    expect(hasPendingExec("<EXEC>a</EXEC><EXEC>b")).toBe(true)
  })
})
