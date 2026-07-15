import { useRef, useEffect } from "react"
import { useWebSocket } from "./hooks/useWebSocket"
import { MessageBubble } from "./components/MessageBubble"
import { InputArea } from "./components/InputArea"
import { ThemeToggle } from "./components/ThemeToggle"
import { StreamingIndicator } from "./components/StreamingIndicator"
import "./theme.css"
import "./App.css"

const WS_URL = "ws://localhost:8765/ws"

function App() {
  const { status, messages, streaming, send } = useWebSocket(WS_URL)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  return (
    <div className="container">
      <div className="status">
        <span>{status === "connected" ? "🟢 已连接" : status === "connecting" ? "🟡 连接中..." : "🔴 已断开"}</span>
        <ThemeToggle />
      </div>

      <div className="messages">
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {streaming && <StreamingIndicator streaming={streaming} />}
        <div ref={bottomRef} />
      </div>

      <InputArea onSend={send} disabled={status !== "connected"} />
    </div>
  )
}

export default App