import { useState, type FormEvent } from "react"

export interface InputAreaProps {
  onSend: (text: string) => void
  disabled: boolean
}

export function InputArea({ onSend, disabled }: InputAreaProps) {
  const [text, setText] = useState("")

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
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
        placeholder="输入消息..."
        autoFocus
        style={{
          flex: 1, padding: "8px 12px", borderRadius: 6,
          border: "1px solid #ddd", fontSize: 14, outline: "none",
        }}
      />
      <button type="submit" disabled={disabled} style={{
        padding: "8px 16px", borderRadius: 6, border: "none",
        background: "#1976d2", color: "#fff", fontSize: 14, cursor: "pointer",
      }}>
        发送
      </button>
    </form>
  )
}