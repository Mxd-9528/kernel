
import { useState, type FormEvent, useRef, useEffect } from "react"

export interface InputAreaProps {
  onSend: (text: string) => void
  onStop: () => void
  disabled: boolean
  streaming: boolean
}

export function InputArea({ onSend, onStop, disabled, streaming }: InputAreaProps) {
  const [text, setText] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // 自动调整高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto"
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + "px"
    }
  }, [text])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (streaming) {
      onStop()
      return
    }
    if (!text.trim()) return
    onSend(text)
    setText("")
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{
      display: "flex", flex: 1, padding: "8px 12px", gap: 8,
      alignItems: "flex-end",
    }}>
      <textarea
        ref={textareaRef}
        className="input-area"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={streaming ? "生成中…" : "输入消息..."}
        autoFocus
        disabled={streaming}
        rows={1}
        style={{
          flex: 1, padding: "6px 10px", borderRadius: 6, fontSize: 14, outline: "none",
          resize: "none", maxHeight: 200, height: "auto",
          fontFamily: "inherit", lineHeight: 1.4,
          border: "1px solid var(--color-hairline-strong)",
          background: "var(--color-surface)",
          color: "var(--color-ink)",
        }}
      />
      <button type="submit" disabled={disabled && !streaming} style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: streaming ? 6 : "8px 16px",
        borderRadius: streaming ? 4 : 6,
        border: "none",
        background: streaming ? "var(--color-muted)" : "var(--color-primary)",
        color: streaming ? "var(--color-canvas)" : "var(--color-on-primary)",
        cursor: "pointer",
        minWidth: streaming ? 36 : 56,
        height: streaming ? 36 : undefined,
        transition: "background 0.15s, border-radius 0.15s",
      }}>
        {streaming ? (
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="3" width="10" height="10" rx="2" />
          </svg>
        ) : (
          "发送"
        )}
      </button>
    </form>
  )
}
