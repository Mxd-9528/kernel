import { describe, it, expect } from "vitest"
import {
  reduceServerMessage,
  pendingMessage,
  type BufferState,
} from "../src/hooks/useWebSocket"
import type { ServerMessage } from "../src/types"

function empty(): BufferState {
  return { messages: [], buffer: "", bufferType: null, tokenCount: 0 }
}

function thinking(token: string): ServerMessage {
  return { jsonrpc: "2.0", method: "window/thinking", params: { token } }
}
function delta(token: string): ServerMessage {
  return { jsonrpc: "2.0", method: "window/delta", params: { token } }
}
function flush(): ServerMessage {
  return { jsonrpc: "2.0", method: "window/flush", params: {} }
}
function display(content: string): ServerMessage {
  return { jsonrpc: "2.0", method: "window/display", params: { content } }
}
function user(content: string): ServerMessage {
  return { jsonrpc: "2.0", method: "window/user", params: { content } }
}

describe("reduceServerMessage — 基础状态机", () => {
  it("thinking token 累积到 buffer，不产消息", () => {
    const s = reduceServerMessage(empty(), thinking("我正在"))
    expect(s.messages).toHaveLength(0)
    expect(s.buffer).toBe("我正在")
    expect(s.bufferType).toBe("thinking")
  })

  it("多个 thinking token 连续累积", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("我"))
    s = reduceServerMessage(s, thinking("正在"))
    s = reduceServerMessage(s, thinking("思考"))
    expect(s.buffer).toBe("我正在思考")
    expect(s.tokenCount).toBe(3)
  })

  it("flush after thinking 产出 thinking 消息，清空 buffer", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("思考内容"))
    s = reduceServerMessage(s, flush())
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.messages[0].content).toBe("思考内容")
    expect(s.buffer).toBe("")
    expect(s.tokenCount).toBe(0)
  })

  it("delta token 累积为 assistant", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("Hello"))
    s = reduceServerMessage(s, delta(" World"))
    s = reduceServerMessage(s, flush())
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("assistant")
    expect(s.messages[0].content).toBe("Hello World")
  })

  it("display 直接产 system 消息，不碰 buffer", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("buf"))
    s = reduceServerMessage(s, display("命令已执行"))
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("system")
    expect(s.buffer).toBe("buf")
  })

  it("user 消息进入历史", () => {
    const s = reduceServerMessage(empty(), user("你好"))
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("user")
    expect(s.messages[0].content).toBe("你好")
  })

  it("flush 空 buffer 不产消息", () => {
    const s = reduceServerMessage(empty(), flush())
    expect(s.messages).toHaveLength(0)
  })

  it("thinking→delta 自动产 thinking 消息", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("思考中"))
    s = reduceServerMessage(s, delta("回答"))
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.buffer).toBe("回答")
    expect(s.bufferType).toBe("delta")
    expect(s.tokenCount).toBe(1)
  })
})

describe("reduceServerMessage — tokenCount", () => {
  it("thinking/delta 递增，flush 归零", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("a"))
    s = reduceServerMessage(s, thinking("b"))
    expect(s.tokenCount).toBe(2)
    s = reduceServerMessage(s, flush())
    expect(s.tokenCount).toBe(0)
    s = reduceServerMessage(s, delta("x"))
    s = reduceServerMessage(s, delta("y"))
    expect(s.tokenCount).toBe(2)
  })

  it("display/user 不影响 tokenCount", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("a"))
    s = reduceServerMessage(s, display("msg"))
    s = reduceServerMessage(s, user("hi"))
    expect(s.tokenCount).toBe(1)
  })
})

describe("pendingMessage — 从 buffer 派生的投影", () => {
  it("空 buffer → null", () => {
    expect(pendingMessage(empty())).toBeNull()
  })

  it("thinking buffer → null（思考内容不流式展示，flush 后才进历史）", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("想..."))
    expect(pendingMessage(s)).toBeNull()
  })

  it("thinking flush 后作为完整消息进入历史", () => {
    let s = empty()
    s = reduceServerMessage(s, thinking("想一想"))
    s = reduceServerMessage(s, thinking("再想想"))
    s = reduceServerMessage(s, flush())
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].role).toBe("thinking")
    expect(s.messages[0].content).toBe("想一想再想想")
    expect(pendingMessage(s)).toBeNull()
  })

  it("delta 纯文本 → assistant pending 全显（无 displayedChars）", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("你好"))
    const p = pendingMessage(s)
    expect(p?.role).toBe("assistant")
    expect(p?.content).toBe("你好")
  })

  it("displayedChars 控制打字机可见前缀", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("你好世界"))
    expect(pendingMessage(s, 0)).toBeNull()
    expect(pendingMessage(s, 2)?.content).toBe("你好")
    expect(pendingMessage(s, 4)?.content).toBe("你好世界")
  })

  it("displayedChars 追到未闭合 EXEC 前缀时，可见部分不含 EXEC 标记", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("你好\n<EXEC>x"))
    // displayedChars=3 只到 "你好\n"，全可见
    expect(pendingMessage(s, 3)?.content).toBe("你好\n")
    // displayedChars=8 打到 "你好\n<EXEC"，EXEC 未闭合被 visiblePrefix 切掉
    expect(pendingMessage(s, 8)?.content).toBe("你好\n")
  })

  it("delta 含未闭合 EXEC → pending 隐藏 EXEC 后的内容", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("你好\n<EXEC>\n```py\nx="))
    const p = pendingMessage(s)
    expect(p?.content).toBe("你好\n")
  })

  it("delta 含已闭合 EXEC → pending 保留完整 EXEC 段", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("<EXEC>a</EXEC>后"))
    const p = pendingMessage(s)
    expect(p?.content).toBe("<EXEC>a</EXEC>后")
  })

  it("delta 只有未闭合 EXEC（visiblePrefix 为空）→ null", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("<EXEC>x"))
    expect(pendingMessage(s)).toBeNull()
  })

  it("flush 后 pending 消失", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("你好"))
    s = reduceServerMessage(s, flush())
    expect(pendingMessage(s)).toBeNull()
  })

  it("flush 完整保留 buffer 含未闭合 EXEC 的残余（防丢内容）", () => {
    let s = empty()
    s = reduceServerMessage(s, delta("<EXEC>未结束"))
    s = reduceServerMessage(s, flush())
    expect(s.messages).toHaveLength(1)
    expect(s.messages[0].content).toBe("<EXEC>未结束")
  })
})
