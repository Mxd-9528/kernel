import { useState, type ReactNode } from "react"
import { Fragment, jsx, jsxs } from "react/jsx-runtime"
import { refractor } from "refractor"
import { toJsxRuntime } from "hast-util-to-jsx-runtime"

interface Props {
  code: string
  language?: string
}

const PREVIEW_LINES = 3

/** 用 refractor 做客户端语法高亮；未注册语言或失败时退化为纯文本。 */
function highlight(code: string, language?: string): ReactNode {
  if (!language || !refractor.registered(language)) return code
  try {
    const tree = refractor.highlight(code, language)
    return toJsxRuntime(tree, { Fragment, jsx, jsxs }) as ReactNode
  } catch {
    return code
  }
}

export function CodeBlock({ code, language }: Props) {
  const lines = code ? code.split("\n") : []
  // 单行不折叠
  if (lines.length <= 1) {
    return (
      <pre className="code-block code-block-inline">
        <code className={language ? `language-${language}` : undefined}>
          {highlight(code, language)}
        </code>
      </pre>
    )
  }

  // 多行：默认折叠，显示前几行预览
  return <CollapsibleCodeBlock code={code} language={language} lines={lines} />
}

function CollapsibleCodeBlock({
  code,
  language,
  lines,
}: { code: string; language?: string; lines: string[] }) {
  const [open, setOpen] = useState(false)

  const preview = lines.slice(0, PREVIEW_LINES).join("\n")
  const hasMore = lines.length > PREVIEW_LINES
  const shown = open ? code : preview

  return (
    <div className="code-block" onClick={() => setOpen(!open)}>
      <pre className={open ? "code-block-body" : "code-block-preview"}>
        <code className={language ? `language-${language}` : undefined}>
          {highlight(shown, language)}
          {hasMore && !open ? "\n..." : ""}
        </code>
      </pre>
    </div>
  )
}