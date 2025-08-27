Product Requirements Document (PRD)
Project Title
AI Face Identity Image Composer with Fine-Tuning
Backend: Nano Banana or fal.ai / Frontend: Claude Code CLI

Problem Statement
Current image generation models (like Astria/Flux) enable creation of character-consistent, photorealistic custom portraits and inpainting. Demand exists for a streamlined, CLI-driven workflow that can fine-tune on a user's images, create new scenes with high identity fidelity, and automatically use inpainting to fix or modify faces as required.

Objectives
Build a CLI tool using Claude Code that:

Allows users to fine-tune an image generation model (Nano Banana, fal.ai) with a set of personal face photos.

Accepts prompts for custom image creation with the tuned face.

Supports automatic face inpainting to correct, edit, or restore facial features while keeping identity consistent.

(Bonus) Flags and displays SynthID watermark detection result for output images.

Functional Requirements
Model Fine-Tuning

User provides a set of ~15-20 images of one individual.

CLI triggers fine-tuning API/job with these images on backend service.

CLI saves model checkpoint/ID for re-use.

Custom Image Creation

User enters a text prompt (“in a sci-fi city”, “at a beach party”, etc.).

CLI calls prompt-to-image functionality using fine-tuned model.

Supports batch mode for generating multiple variants.

Face Inpainting

User may upload or select a generated image for “face inpainting.”

CLI allows prompt/region selection (e.g., “make her smile”, “restore left eye”).

Calls inpainting endpoint via backend service.

Identity Verification/Consistency

Optionally verifies that generated face matches the fine-tuned identity (e.g., using embedding similarity).

Notifies user if result has questionable fidelity.

SynthID Detection

CLI checks if output image has SynthID watermarking.

Displays result to user.

Non-Functional Requirements
CLI must be fully MacOS/Linux compatible (ideally Python, minimal dependencies).

All temp image/model data should be stored locally and removed after session.

Explicit warnings to users: all output is AI-generated, watermarked, and not suitable for deception or impersonation.

API keys/config loaded via environment variables or CLI args (never in codebase).

User Stories
As a user, I can fine-tune the system with my own face, then generate consistent portraits in any scenario I describe.

As a user, I can use inpainting to fix or change my expression in generated photos, or restore damaged regions.

As a user, I can see whether the image contains a SynthID watermark.

As a developer, I can run everything with one simple CLI command and re-use the fine-tuned model any time.

Stretch Goals
Add support for multi-character/stories (multiple fine-tunes).

GUI wrapper for non-CLI users.

Integration with cloud storage for fine-tune/image data.

Technical / Integration: fal.ai API
Authentication
All API interactions require FAL_KEY as an environment variable or runtime argument.

Fine-Tuning Example (flux-lora):

python
import { fal } from "@fal-ai/client";
fal.config({ credentials: "YOUR_FAL_KEY" });

const { request_id } = await fal.queue.submit("fal-ai/flux-lora", {
  input: { training_images: ["img1.jpg", "img2.jpg", ...] },
  webhookUrl: "https://optional.webhook.url/"
});
Prompt-to-Image Generation Example:

python
const result = await fal.subscribe("fal-ai/flux-pro/v1.1-ultra-finetuned", {
  input: {
    prompt: "In a sci-fi city, photorealistic, detailed",
    finetune_id: "YOUR_MODEL_ID"
  },
  logs: true,
  onQueueUpdate: (update) => { /* log updates */ }
});
Face Inpainting Example:

python
const result = await fal.subscribe("fal-ai/flux-pro/v1/fill-finetuned", {
  input: {
    prompt: "restore smile",
    image_url: "original.jpg",
    mask_url: "face_mask.png",
    finetune_id: "YOUR_MODEL_ID"
  },
  logs: true,
  onQueueUpdate: (update) => { /* log updates */ }
});
Queue Handling:

All long tasks return a request_id.

Use polling (fal.queue.status or fal.queue.result) or webhook callback.

References

Docs: https://docs.fal.ai

Flux Model: https://fal.ai/models/fal-ai/flux/dev/api

Inpaint: https://fal.ai/models/fal-ai/inpaint/api

LoRA: https://fal.ai/models/fal-ai/flux-lora/api

Critical Notes
All AI images will be watermarked with SynthID or equivalent.

Images are for creative/personal purposes only—absolutely no deceptive usage.

CLI only (no graphical interface).

API keys/secrets must NOT be visible in commits, logs, or output.


