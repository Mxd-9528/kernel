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
        padding: "8px 16px", borderRadius: 6, border: "none",
        background: streaming ? "#e53935" : "#1976d2",
        color: "#fff", fontSize: 14, cursor: "pointer",
        minWidth: 56,
      }}>
        {streaming ? "■" : "发送"}
      </button>
    </form>
  )
}