/**
 * Minimal Markdown renderer for post bodies.
 *
 * Supports what writers actually use on Liketexts: paragraphs, ##/###
 * headings, bullet lists, numbered lists, **bold**, *italic*, `code`.
 * Everything else stays plain text. All input is HTML-escaped first, so
 * rendered output is safe for v-html.
 */

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Inline formatting on already-escaped text. */
function inline(escaped: string): string {
  return escaped
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>");
}

export function renderMarkdown(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: string[] = [];

  let paragraph: string[] = [];
  let list: { type: "ul" | "ol"; items: string[] } | null = null;

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push(`<p>${inline(escapeHtml(paragraph.join(" ")))}</p>`);
      paragraph = [];
    }
  };

  const flushList = () => {
    if (list) {
      const tag = list.type;
      blocks.push(
        `<${tag}>${list.items.map((i) => `<li>${inline(escapeHtml(i))}</li>`).join("")}</${tag}>`,
      );
      list = null;
    }
  };

  for (const raw of lines) {
    const line = raw.trimEnd();

    if (!line.trim()) {
      flushParagraph();
      flushList();
      continue;
    }
    const h3 = line.match(/^###\s+(.*)$/);
    if (h3) {
      flushParagraph();
      flushList();
      blocks.push(`<h3>${inline(escapeHtml(h3[1]))}</h3>`);
      continue;
    }
    const h2 = line.match(/^##\s+(.*)$/);
    if (h2) {
      flushParagraph();
      flushList();
      blocks.push(`<h2>${inline(escapeHtml(h2[1]))}</h2>`);
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      flushParagraph();
      if (!list || list.type !== "ul") {
        flushList();
        list = { type: "ul", items: [] };
      }
      list.items.push(bullet[1]);
      continue;
    }
    const numbered = line.match(/^\d+\.\s+(.*)$/);
    if (numbered) {
      flushParagraph();
      if (!list || list.type !== "ol") {
        flushList();
        list = { type: "ol", items: [] };
      }
      list.items.push(numbered[1]);
      continue;
    }
    flushList();
    paragraph.push(line.trim());
  }
  flushParagraph();
  flushList();

  return blocks.join("\n");
}
