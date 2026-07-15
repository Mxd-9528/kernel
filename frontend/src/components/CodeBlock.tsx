import { useState } from "react"

interface Props {
  code: string
  language?: string
}

const PREVIEW_LINES = 3

export function CodeBlock({ code, language }: Props) {
  const lines = code ? code.split("\n") : []
  // 单行不折叠
  if (lines.length <= 1) {
    return (
      <pre className="code-block code-block-inline">
        <code>{code}</code>
      </pre>
    )
  }

  // 多行：默认折叠，显示前几行预览
  return <CollapsibleCodeBlock code={code} language={language} lines={lines} />
}

function CollapsibleCodeBlock({
  code,
  lines,
}: { code: string; language?: string; lines: string[] }) {
  const [open, setOpen] = useState(false)

  const preview = lines.slice(0, PREVIEW_LINES).join("\n")
  const hasMore = lines.length > PREVIEW_LINES

  return (
    <div className="code-block" onClick={() => setOpen(!open)}>
      <pre className={open ? "code-block-body" : "code-block-preview"}>
        <code>{open ? code : preview}{hasMore && !open ? "\n..." : ""}</code>
      </pre>
    </div>
  )
}