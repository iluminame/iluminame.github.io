# Styles: the prompt formula and preset library

What a Higgsfield-style platform really sells is *presets* — pre-written
prompts behind pretty thumbnails. This file is that preset library. Combine a
preset with the user's brief to build a production-grade prompt; that is what
makes a $0.05 model output look premium.

## The prompt formula

Build every image prompt in this order (skip fields that don't apply):

```
[SUBJECT — who/what, with concrete details]
[ACTION/POSE — what it's doing]
[SETTING — where, time of day]
[LIGHTING — quality + direction + color]
[CAMERA — shot type, lens, angle, depth of field]
[MOOD/GRADE — palette, film stock, atmosphere]
[TEXT — exact on-image text in "quotes", placement]  ← only models good at text (Nano Banana Pro, FLUX)
[FORMAT — aspect ratio note if the model takes it in-prompt]
```

For **video**, append motion on top of a strong image prompt:

```
[CAMERA MOVE — see camera-move list below]
[SUBJECT MOTION — one clear action, not three]
[PACE — slow and cinematic / fast and punchy]
[AUDIO — only Veo/Sora: ambient sound, dialogue in "quotes"]
```

Rules that consistently improve results:
- One idea per generation. Two subjects doing two things = mush.
- Concrete nouns beat adjectives ("condensation droplets on amber glass" >
  "beautiful refreshing drink").
- Quote any text that must render exactly, and keep it under ~6 words.
- Don't stack style keywords from different presets; pick a lane.
- For ads: leave negative space where the copy/logo will go, and say so in the
  prompt ("upper third empty for headline").

## Image presets

### product-hero
Polished catalog/ad shot of a single product.
> {product} centered on a {surface: polished stone / satin fabric / water ripples},
> studio three-point lighting with soft key and rim light, shot on 85mm lens,
> shallow depth of field, clean {brand color} gradient background, high-end
> commercial photography, upper third empty for headline
Model: nano-banana-pro · Aspect: 1:1 or 4:5

### ugc-ad
Fake-casual phone photo that sells (native-feeling social ad).
> candid iPhone photo of {person} holding {product} in {everyday place}, natural
> window light, slightly imperfect framing, authentic skin texture, no studio
> look, shot on phone camera, casual social media aesthetic
Model: nano-banana / seedream · Aspect: 4:5 or 9:16

### cinematic-still
Movie-frame look for storytelling and covers.
> {subject} in {location}, anamorphic widescreen, dramatic {golden hour /
> blue hour / neon} lighting with deep shadows, atmospheric haze, film grain,
> teal-and-orange grade, shot on 35mm anamorphic lens, cinematic composition
Model: FLUX dev / seedream · Aspect: 16:9 or 21:9

### editorial-fashion
Magazine editorial with attitude.
> {model/subject} wearing {outfit}, {bold pose}, seamless {color} studio
> backdrop, hard directional flash lighting, sharp shadows, high fashion
> editorial for a glossy magazine, medium format look
Model: FLUX 1.1 pro · Aspect: 4:5

### food-macro
Appetite-trigger close-up.
> extreme macro of {dish}, steam rising, glistening texture, dark moody
> background, single dramatic side light, shallow focus on {key detail},
> professional food photography
Model: seedream / nano-banana-pro · Aspect: 1:1

### minimal-luxe
Premium minimalist brand look.
> {product/subject} floating on {monochrome pastel} background, soft even
> lighting, long soft shadow, huge negative space, ultra-minimalist premium
> composition, subtle grain
Model: nano-banana-pro · Aspect: 1:1

### neon-noir
Nighttime tech/urban energy.
> {subject} at night in {rainy city street / dark interior}, saturated neon
> {magenta and cyan} reflections on wet surfaces, volumetric fog, low-angle
> shot, blade-runner atmosphere, high contrast
Model: FLUX dev · Aspect: 16:9 or 9:16

### retro-vhs
Nostalgic analog vibe.
> {subject}, 1980s VHS home-video still, scanlines and chromatic aberration,
> washed-out colors, timestamp in corner, soft analog blur, nostalgic haze
Model: nano-banana · Aspect: 4:3

### 3d-clay
Friendly mascot/explainer style.
> cute 3D claymation-style render of {subject}, soft studio lighting, pastel
> palette, rounded shapes, subtle fingerprint texture in the clay, isometric
> angle, playful mood
Model: nano-banana-pro · Aspect: 1:1

### anime-key-visual
Poster-grade anime frame.
> {character/subject} in {setting}, anime key visual, dynamic composition,
> dramatic sky, crisp lineart, vibrant cel shading, studio-quality anime film
> still, wind-blown motion in hair and clothes
Model: seedream / FLUX dev · Aspect: 16:9 or 2:3

### documentary-bw
Timeless photojournalism.
> {subject} in {real place}, black and white documentary photograph, available
> light only, honest imperfect moment, 35mm film grain, Magnum-photo energy
Model: FLUX dev · Aspect: 3:2

### thumbnail-pop
YouTube/CTR thumbnail.
> {expressive face or object} on {high-contrast solid} background, exaggerated
> expression, rim lighting, bold depth, room on the {left/right} for 3-word
> title text "{TEXT}", ultra-sharp, high saturation
Model: nano-banana-pro (renders text) · Aspect: 16:9

## Video presets

Camera moves that read as "expensive" (the core Higgsfield trick — name the
move explicitly): slow dolly-in, dolly-out reveal, orbit/arc around subject,
crane up, crash zoom, whip pan, FPV fly-through, handheld follow, snorricam,
robo-arm product spin, bullet-time, vertigo/dolly-zoom.

### product-orbit (image→video)
> smooth 180-degree orbit around the product, constant distance, studio
> lighting shifts subtly across surfaces, background softly out of focus,
> slow elegant pace, seamless loop
Model: Kling 2.5 turbo i2v · 5s · from a product-hero image

### cinematic-dolly (image→video or t2v)
> slow dolly-in toward {subject}, atmospheric particles drifting through light
> beams, subtle parallax between foreground and background, cinematic pace
Model: Kling 2.5 / Seedance pro · 5s

### ugc-talking-head (t2v, audio-capable models)
> handheld selfie video of {person} enthusiastically talking to camera in
> {location}, natural daylight, casual energy, they say: "{one-sentence hook}"
Model: Veo 3 fast (native audio) · 8s

### logo-reveal (image→video)
> the logo assembles from {particles / liquid metal / light streaks} on a
> {dark} background, elegant slow build, final frame holds the complete logo
> centered, subtle glow
Model: Seedance pro / Kling · 5s · from a clean logo image

### b-roll-loop (t2v)
> {texture/scene: coffee pouring, waves, city timelapse, fabric flowing},
> seamless loop, rich detail, {slow/fast} rhythm, no text
Model: WAN / Seedance lite · 5s · cheap filler footage

## Choosing for the user

When the brief is vague, map intent → preset: selling a physical product →
product-hero (+ product-orbit); social proof / native ads → ugc-ad; brand
launch → minimal-luxe or editorial-fashion; content thumbnail → thumbnail-pop;
"make it feel like a movie" → cinematic-still (+ cinematic-dolly). Offer the
chosen preset plus ONE alternative, not the whole menu.
