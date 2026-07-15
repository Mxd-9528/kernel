import { useEffect, useState, useRef } from "react"
import type { StreamingState } from "../hooks/useWebSocket"

const LABEL: Record<string, string> = {
  thinking: "💭 思考中",
  delta: "💬 回复中",
}

interface Props {
  streaming: StreamingState
}

export function StreamingIndicator({ streaming }: Props) {
  const startedAt = useRef(Date.now())
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    startedAt.current = Date.now()
    setElapsed(0)
  }, [streaming.phase])

  useEffect(() => {
    const id = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startedAt.current) / 1000))
    }, 1000)
    return () => clearInterval(id)
  }, [])

  return (
    <div className="streaming-indicator">
      {LABEL[streaming.phase]} · {streaming.tokenCount} tokens · {elapsed}s
    </div>
  )
}