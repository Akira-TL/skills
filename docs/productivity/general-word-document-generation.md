# general-word-document-generation

## What it does

This skill generates and revises DOCX files through Word-native document semantics. It builds pages, sections, styles, paragraphs, tables, captions, fields, pagination, and character formatting instead of transferring Markdown or web UI conventions into Word.

Its default output is formal, restrained, printable, and visually stable. Word-native non-image content—including text, headings, tables, fills, borders, shapes, headers, footers, and decorative elements—uses only black, white, and necessary grayscale unless the user explicitly requests color. Images inserted into the document, including photographs, scientific figures, screenshots, maps, exported diagrams, and exported data visualizations, may retain original or informative color.

## When to use it

Use this skill when creating, rewriting, formatting, or quality-checking a general Word document, especially when the result must be ready to submit without manually fixing colored headings, decorative tables, Markdown blockquotes, bullet-heavy prose, unstable pagination, or inconsistent typography.

It adapts to academic papers, research reports, project proposals, business reports, notices, formal statements, operating manuals, and technical documentation. Explicit user, institutional, journal, or project formatting requirements override its defaults.

## Key behavior

The skill starts from a blank DOCX unless the user explicitly requires a supplied template. It defines a coherent Word style system, converts content into semantic document objects, applies character-level scientific formatting where needed, and renders the result page by page for visual inspection before delivery. Color is determined by object type: an exported chart or diagram inserted as an image may remain colored, while editable Word charts, shapes, SmartArt, text boxes, and tables remain non-colored by default.

When revising an existing DOCX under a “text only / keep formatting” constraint, the existing sections, margins, styles, tables, images, captions, headers, footers, fields, and pagination are treated as owned layout. The skill changes only the requested text region and reuses the surrounding paragraph and run formatting instead of normalizing or rebuilding the document.

For academic papers and research reports, the skill also enforces argument structure rather than only typography. Section titles must match what the section actually contains; literature-review claims must be supported by real, verifiable papers; a heading such as “国内外研究进展” is used only when the body actually reviews that literature, otherwise a concrete thematic heading or “相关研究进展” is preferred. Academic prose is organized around the research object, existing evidence, unresolved boundary, and the current study rather than proposal-style formulas such as repeated “研究目的”“旨在” or “为了”. Results state observations and statistics first, while discussion compares evidence, considers mechanisms and alternatives, and keeps conclusions within the resolution of the method. Reference theses are used to learn organization and disciplinary rhetoric, not to transplant their claims, data, or citations.

Chinese text uses full-width Chinese punctuation and “double” or ‘nested’ quotation marks. Latin genus and species names use real italic formatting. Statistical symbols such as *P* use semantic italic formatting rather than visible Markdown markers.

## Source

Runtime instructions are maintained at:

```text
productivity/general-word-document-generation/SKILL.md
```

## 安装

机器级安装只从远端 GitHub source 拉取，并注册到 `~/.agents/skills/`：

```bash
python3 ~/.agents/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill general-word-document-generation
```
