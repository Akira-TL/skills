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

For academic papers and research reports, the skill owns DOCX representation rather than scientific judgement. It can apply section styles, pagination, three-line tables, captions, citation display, scientific italics, equations, and other Word semantics to already-established content. Literature eligibility, scientific argument, Results/Discussion boundaries, causal or mechanistic interpretation, conclusion strength, and provenance remain owned by the upstream research workflow or the user's canonical source. If source content contains a substantive evidence or claim conflict, the skill reports it and returns it to the content owner instead of inventing a second scientific-writing policy. Reference theses and papers may inform transferable document structure and formatting, never transplant claims, data, citations, or scientific conclusions.

Chinese text uses full-width Chinese punctuation and “double” or ‘nested’ quotation marks. Latin genus and species names use real italic formatting. Statistical symbols such as *P* use semantic italic formatting rather than visible Markdown markers.

## Source

Runtime instructions are maintained at:

```text
productivity/general-word-document-generation/SKILL.md
```

## 安装

机器级安装只从远端 GitHub source 拉取，并注册到 `~/.agents/skills/`：

```bash
uv run python ~/.agents/skills/akira/scripts/skills.py install \
  https://github.com/Akira-TL/skills.git \
  --skill general-word-document-generation
```
