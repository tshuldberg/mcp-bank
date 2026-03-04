"""
Markup format conversions: HTML ↔ Markdown ↔ Text.
"""

from bs4 import BeautifulSoup, Tag, NavigableString
from markdown_it import MarkdownIt


def html_to_markdown(data: str) -> str:
    soup = BeautifulSoup(data, "lxml")
    return _node_to_markdown(soup.body or soup).strip()


def _node_to_markdown(node) -> str:
    result = []
    for child in node.children:
        if isinstance(child, NavigableString):
            text = str(child)
            if text.strip():
                result.append(text)
        elif isinstance(child, Tag):
            tag = child.name
            inner = _node_to_markdown(child)
            if tag in ("h1",):
                result.append(f"# {inner.strip()}\n")
            elif tag in ("h2",):
                result.append(f"## {inner.strip()}\n")
            elif tag in ("h3",):
                result.append(f"### {inner.strip()}\n")
            elif tag in ("h4",):
                result.append(f"#### {inner.strip()}\n")
            elif tag in ("h5",):
                result.append(f"##### {inner.strip()}\n")
            elif tag in ("h6",):
                result.append(f"###### {inner.strip()}\n")
            elif tag == "p":
                result.append(f"{inner.strip()}\n\n")
            elif tag == "strong" or tag == "b":
                result.append(f"**{inner.strip()}**")
            elif tag in ("em", "i"):
                result.append(f"*{inner.strip()}*")
            elif tag == "code":
                result.append(f"`{inner}`")
            elif tag == "pre":
                code = child.find("code")
                content = code.get_text() if code else inner
                result.append(f"```\n{content}\n```\n")
            elif tag == "a":
                href = child.get("href", "")
                result.append(f"[{inner.strip()}]({href})")
            elif tag == "img":
                alt = child.get("alt", "")
                src = child.get("src", "")
                result.append(f"![{alt}]({src})")
            elif tag == "ul":
                for li in child.find_all("li", recursive=False):
                    result.append(f"- {_node_to_markdown(li).strip()}\n")
            elif tag == "ol":
                for i, li in enumerate(child.find_all("li", recursive=False), 1):
                    result.append(f"{i}. {_node_to_markdown(li).strip()}\n")
            elif tag == "li":
                result.append(inner)
            elif tag == "br":
                result.append("\n")
            elif tag == "hr":
                result.append("\n---\n")
            elif tag == "blockquote":
                for line in inner.strip().splitlines():
                    result.append(f"> {line}\n")
            elif tag in ("table",):
                result.append(_table_to_markdown(child))
            elif tag in ("thead", "tbody", "tr", "th", "td", "div", "span",
                         "section", "article", "main", "header", "footer",
                         "nav", "aside"):
                result.append(inner)
    return "".join(result)


def _table_to_markdown(table: Tag) -> str:
    rows = table.find_all("tr")
    if not rows:
        return ""
    lines = []
    for i, row in enumerate(rows):
        cells = row.find_all(["th", "td"])
        line = "| " + " | ".join(c.get_text(strip=True) for c in cells) + " |"
        lines.append(line)
        if i == 0:
            sep = "| " + " | ".join("---" for _ in cells) + " |"
            lines.append(sep)
    return "\n".join(lines) + "\n"


def html_to_text(data: str) -> str:
    soup = BeautifulSoup(data, "lxml")
    return soup.get_text(separator="\n", strip=True)


def markdown_to_html(data: str) -> str:
    md = MarkdownIt()
    return md.render(data)


def text_to_html(data: str) -> str:
    escaped = data.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f"<pre>{escaped}</pre>"
