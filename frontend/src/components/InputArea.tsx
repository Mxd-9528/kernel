import { useState, type FormEvent } from "react"

export interface InputAreaProps {
  onSend: (text: string) => void
  onStop: () => void
  disabled: boolean
  streaming: boolean
}

export function InputArea({ onSend, onStop, disabled, streaming }: InputAreaProps) {
  const [text, setText] = useState("")

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

  return (
    <form onSubmit={handleSubmit} style={{
      display: "flex", flex: 1, padding: "8px 12px", gap: 8,
    }}>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={streaming ? "生成中…" : "输入消息..."}
        autoFocus
        disabled={streaming}
        style={{
          flex: 1, padding: "8px 12px", borderRadius: 6,
          border: "1px solid #ddd", fontSize: 14, outline: "none",
        }}
      />
      <button type="submit" disabled={disabled && !streaming} style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        padding: streaming ? 6 : "8px 16px",
        borderRadius: streaming ? 4 : 6,
        border: "none",
        background: streaming ? "var(--color-muted)" : "#1976d2",
        color: streaming ? "var(--color-canvas)" : "#fff",
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