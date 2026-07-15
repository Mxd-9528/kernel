import { describe, it, expect } from "vitest"
import {
  reduceServerMessage,
  addUserMessage,
  type BufferState,
  type ServerMessage,
} from "../src/hooks/useWebSocket"

function empty(): BufferState {
  return { messages: [], buffer: "", bufferType: null, tokenCount: 0 }
}

describe("reduceServerMessage", () => {
  it("thinking token → 累积到 buffer，不产消息", () => {
    const msg: ServerMessage = { type: "thinking", token: "我正在" }
    const next = reduceServerMessage(empty(), msg)
    expect(next.messages).toHaveLength(0)
    expect(next.buffer).toBe("我正在")
    expect(next.bufferType).toBe("thinking")
  })

  it("多个 thinking token → 连续累积", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "我" })
    s = reduceServerMessage(s, { type: "thinking", token: "正在" })
    s = reduceServerMessage(s, { type: "thinking", token: "思考" })
    expect(s.buffer).toBe("我正在思考")
    expect(s.bufferType).toBe("thinking")
    expect(s.messages).toHaveLength(0)
  })

  it("flush after thinking → 产出 thinking 消息，清空 buffer", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "思考内容" })
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.messages[0].content).toBe("思考内容")
    expect(s.buffer).toBe("")
    expect(s.bufferType).toBeNull()
  })

  it("delta token → 累积为 assistant", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "delta", token: "你好" })
    expect(s.buffer).toBe("你好")
    expect(s.bufferType).toBe("delta")
    expect(s.messages).toHaveLength(0)
  })

  it("flush after delta → 产出 assistant 消息", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "delta", token: "Hello" })
    s = reduceServerMessage(s, { type: "delta", token: " World" })
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("assistant")
    expect(s.messages[0].content).toBe("Hello World")
  })

  it("display → 直接产出 system 消息，不碰 buffer", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "delta", token: "buf" })
    s = reduceServerMessage(s, { type: "display", content: "命令已执行" })
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("system")
    expect(s.messages[0].content).toBe("命令已执行")
    expect(s.buffer).toBe("buf")
  })

  it("连续多轮：thinking→flush→delta→flush", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "想..." })
    s = reduceServerMessage(s, { type: "flush" })
    s = reduceServerMessage(s, { type: "delta", token: "答" })
    s = reduceServerMessage(s, { type: "delta", token: "案" })
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.messages).toHaveLength(2)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.messages[0].content).toBe("想...")
    expect(s.messages[1].role).toBe("assistant")
    expect(s.messages[1].content).toBe("答案")
    expect(s.buffer).toBe("")
  })

  it("flush 空 buffer → 不产消息", () => {
    const s = reduceServerMessage(empty(), { type: "flush" })
    expect(s.messages).toHaveLength(0)
    expect(s.buffer).toBe("")
  })

  it("thinking→delta 自动产出 thinking 消息（无 flush）", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "思考中" })
    s = reduceServerMessage(s, { type: "delta", token: "回答" })
    // thinking 自动产出
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.messages[0].content).toBe("思考中")
    // delta 开始新 buffer
    expect(s.buffer).toBe("回答")
    expect(s.bufferType).toBe("delta")
    expect(s.tokenCount).toBe(1)
  })
})

describe("reduceServerMessage — tokenCount", () => {
  it("thinking token 递增 tokenCount", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "a" })
    s = reduceServerMessage(s, { type: "thinking", token: "b" })
    s = reduceServerMessage(s, { type: "thinking", token: "c" })
    expect(s.tokenCount).toBe(3)
  })

  it("delta token 递增 tokenCount", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "delta", token: "你" })
    s = reduceServerMessage(s, { type: "delta", token: "好" })
    expect(s.tokenCount).toBe(2)
  })

  it("flush 归零 tokenCount", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "a" })
    s = reduceServerMessage(s, { type: "thinking", token: "b" })
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.tokenCount).toBe(0)
  })

  it("thinking→flush→delta→flush 每阶段独立计数", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "a" })
    s = reduceServerMessage(s, { type: "thinking", token: "b" })
    expect(s.tokenCount).toBe(2)
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.tokenCount).toBe(0)
    s = reduceServerMessage(s, { type: "delta", token: "x" })
    s = reduceServerMessage(s, { type: "delta", token: "y" })
    s = reduceServerMessage(s, { type: "delta", token: "z" })
    expect(s.tokenCount).toBe(3)
    s = reduceServerMessage(s, { type: "flush" })
    expect(s.tokenCount).toBe(0)
  })

  it("display 不影响 tokenCount", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "thinking", token: "a" })
    s = reduceServerMessage(s, { type: "display", content: "msg" })
    expect(s.tokenCount).toBe(1)
  })
})

describe("addUserMessage", () => {
  it("将用户文本追加到消息列表", () => {
    const s = addUserMessage(empty(), "你好")
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("user")
    expect(s.messages[0].content).toBe("你好")
  })

  it("不影响 buffer 状态", () => {
    let s = empty()
    s = reduceServerMessage(s, { type: "delta", token: "buf" })
    s = addUserMessage(s, "新消息")
    expect(s.buffer).toBe("buf")
    expect(s.bufferType).toBe("delta")
    expect(s.messages).toHaveLength(1)
  })
})