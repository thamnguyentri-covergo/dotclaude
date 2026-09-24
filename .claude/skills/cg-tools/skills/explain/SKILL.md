---
name: explain
description: Explain a topic visually using its own real terminology. Use when the user types /explain <topic> or wants a picture-heavy explainer that keeps the exact technical terms, component names, and actor names of the domain.
---

# explain

Explain the topic using a HTML artifact with big pictures and few words.

Rules:
- Use the exact terms, component names, and actor names from the domain. HTTPS → server, client, certificate, CA, public/private key, TLS handshake, session key.
- No metaphors, no analogies, no stand-in names (no envelope, no lockbox, no Alice and Bob).
- Diagrams carry the explanation. Text is labels and short captions only.
- Show the real sequence and the real data that moves between components.
- Always draw all visuals and diagrams in Excalidraw hand-drawing style: wobbly/jagged strokes, hachure fill, handwriting font (e.g. Patrick Hand) — like a whiteboard sketch, never clean vector style.
- Never label a shape with bare `<text>` — SVG text does not wrap, so paths, commands and flags spill over the border. Cover the shape with a `<foreignObject>` at its exact x/y/width/height, holding one wrapping div. Only free-floating captions stay `<text>`.

```html
<foreignObject x="52" y="196" width="262" height="118"><div class="lbl">allowed_tools: [Read, Grep, Skill]</div></foreignObject>
<style>.lbl{box-sizing:border-box;height:100%;padding:9px 13px;display:flex;flex-direction:column;justify-content:center;overflow-wrap:anywhere}</style>
```

Topic: $ARGUMENTS
