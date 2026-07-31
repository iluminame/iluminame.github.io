# From one image to a full website

The follow-up that turns a $0.05 image into a shippable asset: take the best
generated image and build a landing page around it. Total marginal cost: $0.

## When to offer it

After generating a strong hero/product image, or when the user says anything
like "now make a page/landing/website for this". Don't build it unprompted —
offer it once (workflow step 7) and proceed on a yes.

## Workflow

1. **Pick the hero.** Use the image the user liked (ask only if several
   candidates are equally plausible). Copy it from `generations/…` into the
   site folder as `site/<slug>/assets/hero.<ext>` — the page must reference the
   local copy, never a provider URL (they expire).

2. **Extract the palette from the image.** The page should look like it was
   designed around the image because it was. Pull 3 colors:
   - dominant background tone → page background
   - the image's strongest accent → CTA buttons and highlights
   - a near-black or near-white from the image → text color
   No dependencies needed: sample with Python/PIL if available, otherwise
   eyeball from the image directly (you can read image files).

3. **Write the copy from the original brief.** The generation brief already
   contains the product, audience, and angle. Structure:
   - Headline: the outcome the buyer wants (≤8 words)
   - Subheadline: how the product gets them there (1 sentence)
   - 3 benefit bullets (not features)
   - 1 CTA, repeated top and bottom ("Get X", never "Submit")
   - Optional: social-proof strip, FAQ (3 items)
   Match the language of the user's brief (Spanish brief → Spanish page).

4. **Build a single self-contained file** at `site/<slug>/index.html`:
   inline CSS, no frameworks, no CDN fonts (use system font stacks), semantic
   HTML, mobile-first with the hero image ≤100% width. Layout: full-bleed hero
   (image + headline + CTA overlaid or side-by-side), benefits section, CTA
   section, minimal footer. Keep it under ~300 lines.

5. **More assets, same skill.** If the page needs supporting visuals
   (feature icons, background texture, second product angle), generate them
   with the same style preset so the page stays coherent — mention the added
   cost first as usual (usually 2–3 × $0.02 drafts).

6. **Ship it.** Tell the user how to publish:
   - Already inside a `*.github.io` repo (like this one): commit `site/<slug>/`
     and it's live at `https://<user>.github.io/site/<slug>/` once pushed.
   - Otherwise: drag-and-drop folder to Netlify, or `vercel deploy`.

## Quality bar

The page passes when: the hero image is the visual anchor (not a decoration),
palette demonstrably comes from the image, there is exactly one CTA action,
it reads well on a phone-width viewport, and the total page weight is just the
image plus a few KB of HTML.
