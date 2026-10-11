import { describe, expect, it } from "vitest";
import { renderMarkdown } from "./markdown";

describe("renderMarkdown", () => {
  it("escapes HTML before rendering", () => {
    expect(renderMarkdown("<script>alert(1)</script>")).toBe(
      "<p>&lt;script&gt;alert(1)&lt;/script&gt;</p>",
    );
  });

  it("renders headings and inline styles", () => {
    expect(renderMarkdown("## Title\n\nSome **bold** and *soft* text")).toBe(
      "<h2>Title</h2>\n<p>Some <strong>bold</strong> and <em>soft</em> text</p>",
    );
  });

  it("groups bullet and numbered lists", () => {
    expect(renderMarkdown("- a\n- b\n\n1. one\n2. two")).toBe(
      "<ul><li>a</li><li>b</li></ul>\n<ol><li>one</li><li>two</li></ol>",
    );
  });

  it("renders inline code", () => {
    expect(renderMarkdown("run `make seed` now")).toBe(
      "<p>run <code>make seed</code> now</p>",
    );
  });

  it("joins soft-wrapped lines into one paragraph", () => {
    expect(renderMarkdown("one\n\ntwo\nthree")).toBe(
      "<p>one</p>\n<p>two three</p>",
    );
  });
});
