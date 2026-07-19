
import { useState } from "react"
import Markdown from "react-markdown"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
// 子路径 /common 只打包主流 40+ 语言（vs default 入口的 all 版 200+）
import rehypePrism from "rehype-prism-plus/common"
import rehypeKatex from "rehype-katex"
import "katex/dist/katex.min.css"
import type { PluggableList } from "unified"
import type { RenderedMessage } from "../types"
import { splitByExec } from "../lib/segments"
import { CodeBlock } from "./CodeBlock"
import { EditDiffView, parseEditCall } from "./EditDiffView"

const rehypePlugins: PluggableList = [[rehypePrism, { ignoreMissing: true }], rehypeKatex]

export interface MessageBubbleProps {
  message: RenderedMessage
}

export function MessageBubble({ message }: MessageBubbleProps) {
  if (message.role === "thinking") {
    return <ThinkingBubble content={message.content} />
  }

  if (message.role === "assistant") {
    const segments = splitByExec(message.content)
    return (
      <div className="bubble bubble-assistant">
        {segments.map((seg, i) => {
          if (seg.type === "text") {
            return (
              <Markdown key={i} remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={rehypePlugins} components={textComponents}>
                {seg.content}
              </Markdown>
            )
          }
          return <ExecSegment key={i} content={seg.content} />
        })}
      </div>
    )
  }

  return (
    <div className={`bubble bubble-${message.role}`}>
      <pre className="bubble-text">{message.content}</pre>
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

/** EXEC 段：从围栏代码块提取代码后走可折叠 CodeBlock（或 EditDiffView）。 */
function ExecSegment({ content }: { content: string }) {
  const { code, language } = parseFence(content)
  const editDiff = parseEditCall(code)
  if (editDiff) return <EditDiffView code={code} diff={editDiff} />
  return <CodeBlock code={code} language={language} />
}

/** 从 EXEC 段内容中提取围栏代码块的代码与语言。无围栏则原样返回。 */
function parseFence(content: string): { code: string; language?: string } {
  const match = content.match(/^\s*```([\w-]*)\n([\s\S]*?)\n```\s*$/)
  if (!match) return { code: content.trim() }
  return { code: match[2], language: match[1] || undefined }
}

// ── markdown 组件配置 ───────────────────────────────────
// 讲解代码块（非 EXEC）永远不折叠——CodeBlock 只由 ExecSegment 使用。

const textComponents = {
  // rehype-prism 已在 hast 层把 <code> 内容替换为 token spans，透传 children 保留结构
  // 不透传 node（react-markdown 内部字段），并合并 rehype 加的 language-* class
  pre({ children, className, node: _node, ...props }: any) {
    const merged = ["md-code-block", className].filter(Boolean).join(" ")
    return <pre className={merged} {...props}>{children}</pre>
  },
  code({ className, children, node: _node, ...props }: any) {
    // 行内 code 不含 language-* class，rehype-prism 也不会碰它
    const isInline = !className || !/language-/.test(className)
    if (isInline) {
      return <code className="md-inline-code" {...props}>{children}</code>
    }
    return <code className={className} {...props}>{children}</code>
  },
  a({ href, children, node: _node }: any) {
    return <a href={href} target="_blank" rel="noopener">{children}</a>
  },
}
