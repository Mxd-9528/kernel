import { describe, it, expect, vi, beforeAll, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import App from "../src/App"

// jsdom 未实现 scrollIntoView
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})
afterEach(() => cleanup())

// Mock useWebSocket — 不发起真实连接
vi.mock("../src/hooks/useWebSocket", () => ({
  useWebSocket: () => ({
    status: "connected",
    messages: [
      { id: "1", role: "user" as const, content: "你好" },
      { id: "2", role: "assistant" as const, content: "你好！" },
    ],
    streaming: null,
    send: vi.fn(),
  }),
}))

describe("App", () => {
  it("渲染消息列表", () => {
    render(<App />)
    expect(screen.getByText("你好")).toBeTruthy()
    expect(screen.getByText("你好！")).toBeTruthy()
  })

  it("有输入框和发送按钮", () => {
    render(<App />)
    expect(screen.getByPlaceholderText("输入消息...")).toBeTruthy()
    expect(screen.getByText("发送")).toBeTruthy()
  })
})