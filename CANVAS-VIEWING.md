# How to see the workplan Canvas (Windows)

If you only see **TypeScript code** or a **tiny/blank** panel, follow these steps in order.

## 1. Sync the canvas (one command)

In PowerShell, from the workshop folder:

```powershell
cd C:\Users\idoza\topfull-retryguard-workshop
powershell -ExecutionPolicy Bypass -File scripts\sync-canvas-to-cursor.ps1
```

## 2. Open the live Canvas (important)

Do **not** rely on the repo file `canvases\topfull-retryguard-workplan.canvas.tsx` alone.

1. Press **`Ctrl+Shift+P`**
2. Type **`Open Canvas`**
3. Choose **`topfull-retryguard-workplan`**

If **Open Canvas** is missing:

- `Ctrl+Shift+P` → **Open Editor Window**, then try **Open Canvas** again
- Update Cursor to the latest version

## 3. Optional: open the managed file first

**File → Open File** and paste:

```
C:\Users\idoza\.cursor\projects\c-Users-idoza-topfull-retryguard-workshop\canvases\topfull-retryguard-workplan.canvas.tsx
```

Then run **Open Canvas** (step 2).

## 4. Make it readable

- **Drag** the split between code and Canvas to give the Canvas side more space
- **Scroll** inside the Canvas panel (not only the code editor)
- Open **one phase** at a time, then **one step** inside it (steps are collapsible)

## Still not working?

| What you see | What to do |
|--------------|------------|
| Red `Cannot find module 'cursor/canvas'` on repo file | Normal for repo copy; use **Open Canvas** on managed file |
| Completely blank Canvas | Run sync script again; restart Cursor; check VPN/firewall blocking localhost |
| Long wall of text | Re-run sync (layout was updated: phases first, steps collapsed) |

## Fallback: markdown workplan

Open [WORKPLAN.md](WORKPLAN.md) — same content, works in any editor without Canvas.
