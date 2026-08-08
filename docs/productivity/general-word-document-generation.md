# general-word-document-generation

## What it does

This skill generates and revises DOCX files through Word-native document semantics. It builds pages, sections, styles, paragraphs, tables, captions, fields, pagination, and character formatting instead of transferring Markdown or web UI conventions into Word.

Its default output is formal, restrained, printable, and visually stable. Word-native non-image content—including text, headings, tables, fills, borders, shapes, headers, footers, and decorative elements—uses only black, white, and necessary grayscale unless the user explicitly requests color. Images inserted into the document, including photographs, scientific figures, screenshots, maps, exported diagrams, and exported data visualizations, may retain original or informative color.

## When to use it

Use this skill when creating, rewriting, formatting, or quality-checking a general Word document, especially when the result must be ready to submit without manually fixing colored headings, decorative tables, Markdown blockquotes, bullet-heavy prose, unstable pagination, or inconsistent typography.

It adapts to academic papers, research reports, project proposals, business reports, notices, formal statements, operating manuals, and technical documentation. Explicit user, institutional, journal, or project formatting requirements override its defaults.

## Key behavior

The skill starts from a blank DOCX unless the user explicitly requires a supplied template. It defines a coherent Word style system, converts content into semantic document objects, applies character-level scientific formatting where needed, and renders the result page by page for visual inspection before delivery. Color is determined by object type: an exported chart or diagram inserted as an image may remain colored, while editable Word charts, shapes, SmartArt, text boxes, and tables remain non-colored by default.

Chinese text uses full-width Chinese punctuation and “double” or ‘nested’ quotation marks. Latin genus and species names use real italic formatting. Statistical symbols such as *P* use semantic italic formatting rather than visible Markdown markers.

## Source

Runtime instructions are maintained at:

```text
productivity/general-word-document-generation/SKILL.md
```

## 安装

从当前仓库安装：

```bash
npx skills add . --skill general-word-document-generation --agent codex -g -y
```

也可以直接从 GitHub 安装：

```bash
npx skills add Akira-TL/skills --skill general-word-document-generation --agent codex -g -y
```
