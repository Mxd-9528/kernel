
import { useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import type { RenderedMessage } from "../types"
import { CodeBlock } from "./CodeBlock"
import { EditDiffView, parseEditCall } from "./EditDiffView"

export interface MessageBubbleProps {
  message: RenderedMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "thinking") {
    return <ThinkingBubble content={message.content} />
  }

  const content = message.role === "assistant"
    ? message.content.replace(/<\/?EXEC>/g, "")
    : message.content

  return (
    <div className={`bubble bubble-${message.role}`}>
      {message.role === "assistant" ? (
        <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>{content}</Markdown>
      ) : (
        <pre className="bubble-text">{content}</pre>
      )}
    </div>
  )
}

function ThinkingBubble({ content }: { content: string }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="bubble bubble-thinking" onClick={() => setOpen(!open)}>
      <div className="thinking-header">
        <span>{open ? "▼" : "▶"} 思考过程</span>
      </div>
      {open && <pre className="bubble-text">{content}</pre>}
    </div>
  )
}

const mdComponents = {
  pre({ children }: any) {
    const codeEl = children
    const className = codeEl?.props?.className || ""
    const language = className.replace("language-", "")
    const code = codeEl?.props?.children?.toString() || ""

    // 检测是否是 edit 调用
    const editDiff = parseEditCall(code)
    if (editDiff) {
      return <EditDiffView code={code} diff={editDiff} />
    }

    // 普通代码块
    const lines = code ? code.split("\n") : []
    if (lines.length <= 1) {
      return <pre className="code-block code-block-inline"><code>{code}</code></pre>
    }
    return <CodeBlock code={code} language={language || undefined} />
  },
  code({ className, children, ...props }: any) {
    const inline = !className
    if (inline) {
      return <code className="md-inline-code" {...props}>{children}</code>
    }
    return <code className={className} {...props}>{children}</code>
  },
  a({ href, children }: any) {
    return <a href={href} target="_blank" rel="noopener">{children}</a>
  },
}
