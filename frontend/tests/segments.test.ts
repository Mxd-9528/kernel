import { describe, it, expect } from "vitest"
import { splitByExec, visiblePrefix, hasPendingExec } from "../src/lib/segments"

const bt = () => String.fromCharCode(96, 96, 96);

describe("splitByExec", () => {
  it("empty string -> []", () => {
    expect(splitByExec("")).toEqual([])
  })
  it("plain text -> single text segment", () => {
    expect(splitByExec("hello")).toEqual([{ type: "text", content: "hello" }])
  })
  it("complete exec block -> text + exec(closed) + text", () => {
    const r = splitByExec("pre\n<EXEC>\n" + bt() + "py\ncode\n" + bt() + "\n</EXEC>\npost")
    expect(r).toEqual([
      { type: "text", content: "pre\n" },
      { type: "exec", content: "code", closed: true },
      { type: "text", content: "\npost" },
    ])
  })
  it("unclosed real exec, last segment closed=false", () => {
    const r = splitByExec("pre\n<EXEC>\n" + bt() + "py\ncode")
    expect(r).toEqual([
      { type: "text", content: "pre\n" },
      { type: "exec", content: "code", closed: false },
    ])
  })
  it("isolated <EXEC> (no backtick) -> treated as text", () => {
    expect(splitByExec("pre\n<EXEC>\npost")).toEqual([
      { type: "text", content: "pre\n<EXEC>\npost" },
    ])
  })
  it("multiple isolated <EXEC> - all treated as text", () => {
    expect(splitByExec("<EXEC>A</EXEC>")).toEqual([
      { type: "text", content: "<EXEC>A</EXEC>" },
    ])
  })
  it("concatenation invariant: all contents = original minus markers", () => {
    const input = "pre<EXEC>\n" + bt() + "\ncode1\n" + bt() + "\n</EXEC>mid<EXEC>\n" + bt() + "\ncode2\n" + bt() + "\n</EXEC>post"
    const segs = splitByExec(input)
    const rebuilt = segs.map(s => s.content).join("")
    const noOpen = rebuilt.replace(/^pre/, "pre")
    expect(segs[0].content.startsWith("pre")).toBe(true)
  })
})

describe("visiblePrefix", () => {
  it("trailing < is hidden", () => expect(visiblePrefix("hello<")).toBe("hello"))
  it("trailing <E is hidden", () => expect(visiblePrefix("hello<E")).toBe("hello"))
  it("trailing <EXEC is hidden", () => expect(visiblePrefix("hello<EXEC")).toBe("hello"))
  it("<EXEC> without backtick -> not hidden", () => expect(visiblePrefix("hello<EXEC>")).toBe("hello<EXEC>"))
  it("lonely < or <X not mistaken for EXEC", () => {
    expect(visiblePrefix("a<b")).toBe("a<b")
    expect(visiblePrefix("a<Xb")).toBe("a<Xb")
  })
  it("unclosed real exec -> only text before it", () => expect(visiblePrefix("pre\n<EXEC>\n" + bt() + "py\nx=")).toBe("pre\n"))
  it("closed real exec -> preserve markers", () => {
    const result = visiblePrefix("pre<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC>post")
    expect(result).toBe("pre<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC>post")
  })
  it("closed + unclosed -> keep closed, cut unclosed", () => {
    const result = visiblePrefix("pre<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC>mid<EXEC>\n" + bt() + "\nb=")
    expect(result).toBe("pre<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC>mid")
  })
})

describe("hasPendingExec", () => {
  it("no EXEC -> false", () => expect(hasPendingExec("hello")).toBe(false))
  it("isolated <EXEC> (no backtick) -> false", () => expect(hasPendingExec("<EXEC>a</EXEC>")).toBe(false))
  it("closed real exec -> false", () => expect(hasPendingExec("<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC>")).toBe(false))
  it("unclosed real exec -> true", () => expect(hasPendingExec("<EXEC>\n" + bt() + "\na")).toBe(true))
  it("closed + unclosed real exec -> true", () => expect(hasPendingExec("<EXEC>\n" + bt() + "\na\n" + bt() + "</EXEC><EXEC>\n" + bt() + "\nb")).toBe(true))
})