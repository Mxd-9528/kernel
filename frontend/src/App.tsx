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
  const { status, messages, streaming, send, interrupt } = useWebSocket(WS_URL)
  const bottomRef = useRef<HTMLDivElement>(null)
  const messagesRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = messagesRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
    if (atBottom) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  return (
    <div className="container">
      <div className="messages" ref={messagesRef}>
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {streaming && <StreamingIndicator streaming={streaming} />}
        <div ref={bottomRef} />
      </div>

      <div className="bottom-bar">
        <ThemeToggle />
        <InputArea
          onSend={send}
          onStop={interrupt}
          disabled={status !== "connected"}
          streaming={streaming !== null}
        />
      </div>
    </div>
  )
}

export default App