# ADR-004: No Full-Frame AI Video Regeneration In V0.1

Date: 2026-06-23

Status: Accepted for V0.1 spike planning

## Context

CineAnchor V0.1 needs stable promotional MP4 output from Blender Eevee and FFmpeg. Route 3A validated that ComfyUI can process extracted keyframes, but direct full-frame SDXL img2img corrupted rendered subtitle text in 4 of 4 reviewed `character_intro` frames.

The Web to local render chain is already validated through FastAPI, Project JSON, Blender Eevee Headless, FFmpeg, and MP4 download. Adding full-frame AI video regeneration would create instability before the core V0.1 path is ready.

## Decision

Full-frame AI video regeneration is excluded from V0.1.

V0.1 only allows conservative AI-assisted color/style reference. Final full-video enhancement must remain FFmpeg, LUT, or filter based. ComfyUI can generate reference stills for color direction, but it must not replace final frames in V0.1.

## Reasons

1. Frame-to-frame flicker risk is high when individual video frames are regenerated.
2. Subject deformation risk is unacceptable for character and product promo output.
3. Output quality is unstable and difficult to guarantee across arbitrary frames.
4. Processing time is unacceptable for the V0.1 local workflow. For example, processing 240 frames through ComfyUI can exceed 30 minutes.
5. Previous direct full-frame img2img corrupted rendered subtitle text, even with a conservative low-denoise workflow.

## Consequences

- ComfyUI must not replace final frames in V0.1.
- Text-bearing final frames should remain Blender/FFmpeg output.
- Any optional AI enhancement must be stable video-wide color grading, LUT, or filter enhancement.
- Future AI enhancement retries should happen before text compositing, or use masks/post-processing that preserve original text pixels.

## 2026-06-24 Feasibility Gate Update

An isolated AI enhancement feasibility gate tested the next retry: render
`character_intro` without text, run ComfyUI img2img on no-text frames, then add
title/subtitle afterward through FFmpeg.

This fixed text stability but did not pass the product gate. Denoise `0.25` was
the only plausible stability setting, but visual lift was weak. Denoise `0.35`
and `0.50` gave a stronger AI look but changed character/product details and
introduced unacceptable deformation risk.

Decision impact:

- ADR-004 remains accepted for V0.1.
- ComfyUI still must not enter the production Web/FastAPI render path.
- Post-AI text overlay is a valid mitigation for text corruption, but it does
  not make frame-by-frame AI regeneration product-ready.
- Continue AI enhancement only as a separate research track with a different
  temporally consistent or masked method.
