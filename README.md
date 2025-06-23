# V_Artemis.py - Diffusion Model Script

`V_Artemis.py` is a core component of a diffusion model, designed for image generation. It implements the U-Net architecture, provides utilities for diffusion processes, and supports both Denoising Diffusion Probabilistic Models (DDPM) and Denoising Diffusion Implicit Models (DDIM) for sampling.

## Features

-   **U-Net Architecture:** Implements a standard U-Net for noise prediction in the diffusion process.
-   **Diffusion Schedules:** Supports linear and cosine beta schedules for diffusion.
-   **DDPM & DDIM Sampling:** Provides functions for both DDPM and DDIM sampling, allowing flexibility in image generation.
-   **Model Management:** Includes utilities for saving, loading, and listing available models.
-   **Image Handling:** Functions for saving generated image tensors to files.
-   **Progress Streaming:** Integrates `tqdm` for streaming progress updates, useful for web integration (as suggested by `TqdmToSSE` and `generate_for_web`).

## Core Components

### `Unet` Class

The neural network responsible for predicting noise in the diffusion process. It takes an image, a time embedding, and optional class labels as input.

### Diffusion Utilities

-   `linear_beta_schedule` and `cosine_beta_schedule`: Functions to define the noise schedule over time steps.
-   `precompute_diffusion_terms`: Prepares various terms required for the forward and reverse diffusion processes.

### Samplers

-   `ddpm_sample`: Implements a single step of the DDPM sampling process.
-   `ddim_sample`: Implements a single step of the DDIM sampling process.

### Generation Functions

-   `p_sample_pass`: The main sampling loop that iteratively refines an image.
-   `generate_images`: Orchestrates the image generation process, including setting up the model and saving outputs.
-   `generate_for_web`: (Inferred) A function designed to expose image generation functionality, likely for web applications, providing progress updates.

## Setup and Usage

To use `V_Artemis.py`, you will need to have PyTorch and other dependencies installed.

### Dependencies

Assuming a `requirements.txt` exists (as seen in directory listing), you can install dependencies using pip:

```bash
pip install -r requirements.txt
```

### Model Storage

Models are saved and loaded from the `models/` directory. The default model name is `default_model`.
