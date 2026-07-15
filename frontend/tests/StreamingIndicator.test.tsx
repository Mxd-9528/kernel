import { describe, it, expect, vi, afterEach } from "vitest"
import { render, screen, cleanup } from "@testing-library/react"
import { StreamingIndicator } from "../src/components/StreamingIndicator"

afterEach(() => cleanup())

describe("StreamingIndicator", () => {
  it("thinking 阶段显示思考中", () => {
    vi.useFakeTimers()
    render(<StreamingIndicator streaming={{ phase: "thinking", tokenCount: 42 }} />)
    expect(screen.getByText(/思考中/)).toBeTruthy()
    expect(screen.getByText(/42 tokens/)).toBeTruthy()
    vi.useRealTimers()
  })

  it("delta 阶段显示回复中", () => {
    vi.useFakeTimers()
    render(<StreamingIndicator streaming={{ phase: "delta", tokenCount: 128 }} />)
    expect(screen.getByText(/回复中/)).toBeTruthy()
    expect(screen.getByText(/128 tokens/)).toBeTruthy()
    vi.useRealTimers()
  })
})