import { describe, it, expect, vi, beforeAll, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import "@testing-library/jest-dom/vitest"
import { InputArea } from "../src/components/InputArea"

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn()
})
afterEach(() => cleanup())

describe("InputArea", () => {
  it("输入文本后点击发送 → 触发 onSend", async () => {
    const onSend = vi.fn()
    render(<InputArea onSend={onSend} disabled={false} />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText("输入消息..."), "你好")
    await user.click(screen.getByText("发送"))

    expect(onSend).toHaveBeenCalledWith("你好")
  })

  it("disabled 时 → 按钮禁用", () => {
    render(<InputArea onSend={vi.fn()} disabled={true} />)
    expect(screen.getByText("发送")).toBeDisabled()
  })

  it("回车提交", async () => {
    const onSend = vi.fn()
    render(<InputArea onSend={onSend} disabled={false} />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText("输入消息..."), "你好{Enter}")

    expect(onSend).toHaveBeenCalledWith("你好")
  })

  it("发送后清空框", async () => {
    const onSend = vi.fn()
    render(<InputArea onSend={onSend} disabled={false} />)
    const user = userEvent.setup()

    await user.type(screen.getByPlaceholderText("输入消息..."), "你好")
    await user.click(screen.getByText("发送"))

    expect(screen.getByPlaceholderText("输入消息...")).toHaveValue("")
  })
})