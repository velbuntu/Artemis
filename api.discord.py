# ---------------------------------------------------------------------------- #
# Copyright (C) 2025 V.Labs, a branch of Vel Ltd. All rights reserved.         #
#                                                                              #
# V.Artemis - Discord Bot Client for V.Artemis API                             #
#                                                                              #
# This bot demonstrates how to interact with the V.Artemis API, a              #
# generative AI framework developed by V.Labs, via Discord commands.           #
#                                                                              #
# THE FOLLOWING SOFTWARE IS FOR PERSONAL USE ONLY                              #
#                                                                              #
# ---------------------------------------------------------------------------- #

import os
import requests
import sys
import io
import discord
from discord.ext import commands
from discord import app_commands # For slash commands

# --- Configuration ---
# Set these as environment variables for security (recommended)
# On Linux/macOS: export ARTEMIS_API_KEY="your_key_here"
# On Windows:     set ARTEMIS_API_KEY="your_key_here"
ARTEMIS_API_KEY = os.environ.get("ARTEMIS_API_KEY")

# Get your Discord bot token from Discord Developer Portal
# On Linux/macOS: export DISCORD_TOKEN="your_discord_bot_token"
# On Windows:     set DISCORD_TOKEN="your_discord_bot_token"
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")

BASE_URL = "http://127.0.0.1:5000/api/v1" # Your Artemis API server URL

# --- Discord Bot Setup ---
# Define intents. Message Content Intent is required for bots that read message content.
# For slash commands, it's less critical, but good to have for general bot functionality.
intents = discord.Intents.default()
intents.message_content = True # Required for reading message content (e.g., if you add non-slash commands later)

bot = commands.Bot(command_prefix="!", intents=intents)

# Store available models globally for autocomplete and validation
available_models_cache = []

# --- API Interaction Functions (Adapted from original script) ---

def get_authenticated_headers():
    """Checks for the API key and returns the required headers."""
    if not ARTEMIS_API_KEY or ARTEMIS_API_KEY == "YOUR_API_KEY_HERE":
        raise ValueError("ARTEMIS_API_KEY not configured. Please set the environment variable or hardcode it.")
    return {"X-API-Key": ARTEMIS_API_KEY}

def make_api_request(method, endpoint, headers, json_payload=None):
    """Makes a generic request to the API and handles errors."""
    url = f"{BASE_URL}/{endpoint}"
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=json_payload)
        else:
            raise ValueError("Unsupported HTTP method")

        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as e:
        error_details = f"API Error {e.response.status_code} {e.response.reason}"
        try:
            json_error = e.response.json()
            error_details += f": {json_error.get('error', 'No details provided.')}"
        except requests.exceptions.JSONDecodeError:
            error_details += f": {e.response.text}"
        raise Exception(error_details)
    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection Error: Could not connect to {url}. Is the server running? Details: {e}")

# --- Discord Bot Events ---

@bot.event
async def on_ready():
    """Called when the bot is ready and connected to Discord."""
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    print("------")
    try:
        # Sync slash commands with Discord
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        
        # Initial fetch of models
        global available_models_cache
        headers = get_authenticated_headers()
        models_data = make_api_request('GET', 'models', headers)
        if models_data and models_data.get("models"):
            available_models_cache = models_data["models"]
            print(f"Fetched {len(available_models_cache)} models successfully.")
        else:
            print("[WARNING] Could not fetch models on startup. Model autocomplete might not work.")

    except Exception as e:
        print(f"[ERROR] Failed to sync commands or fetch models: {e}")
        print("Please ensure your ARTEMIS_API_KEY and BASE_URL are correct and the API server is running.")

# --- Autocomplete function for models ---
async def model_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice]:
    """
    Provides autocomplete suggestions for model names based on the cached available models.
    """
    return [
        app_commands.Choice(name=model['name'], value=model['name'])
        for model in available_models_cache if current.lower() in model['name'].lower()
    ][:25] # Limit to 25 choices for autocomplete


# --- Discord Slash Commands ---

@bot.tree.command(name="generate", description="Generate an image using V.Artemis AI.")
@app_commands.describe(
    model_name="The name of the model to use (e.g., StableDiffusion)",
    prompt="The text prompt for the image generation.",
    sampler="The sampler to use (DDIM (fast) or DDPM (quality)). Default is DDIM.",
    num_images="The number of images to generate (1-20). Default is 1."
)
@app_commands.autocomplete(model_name=model_autocomplete)
async def generate(
    interaction: discord.Interaction,
    model_name: str,
    prompt: str,
    sampler: str = "DDIM",
    num_images: app_commands.Range[int, 1, 20] = 1
):
    """
    Generates an image using the V.Artemis API based on the provided prompt and settings.
    """
    await interaction.response.defer() # Acknowledge the command immediately to prevent timeout

    try:
        headers = get_authenticated_headers()
    except ValueError as e:
        await interaction.followup.send(f"❌ Configuration Error: {e}", ephemeral=True)
        return

    # --- Fetch Models (in case cache is stale or failed on startup) ---
    global available_models_cache
    if not available_models_cache:
        try:
            models_data = make_api_request('GET', 'models', headers)
            if models_data and models_data.get("models"):
                available_models_cache = models_data["models"]
            else:
                await interaction.followup.send("❌ Error: Could not fetch available models from the API.", ephemeral=True)
                return
        except Exception as e:
            await interaction.followup.send(f"❌ Error fetching models: {e}", ephemeral=True)
            return

    # --- Validate Model ---
    chosen_model_obj = next((m for m in available_models_cache if m['name'].lower() == model_name.lower()), None)
    if not chosen_model_obj:
        model_names = ", ".join([m['name'] for m in available_models_cache])
        await interaction.followup.send(
            f"❌ Invalid model name: `{model_name}`. Available models are: `{model_names}`. "
            "Please use the autocomplete suggestions.", ephemeral=True
        )
        return

    # --- Prepare Payload ---
    payload = {
        "model_name": chosen_model_obj['name'],
        "prompt": prompt,
        "sampler": sampler,
        "num_images": num_images
    }

    # --- Send Generation Request ---
    try:
        await interaction.followup.send(
            f"✨ Generating {num_images} image(s) using `{chosen_model_obj['name']}` "
            f"with prompt: `{prompt}` (Sampler: `{sampler}`). This may take a moment...",
            ephemeral=False # Send visible message
        )
        response_data = make_api_request('POST', 'generate', headers, json_payload=payload)

        if response_data and response_data.get('success'):
            images_data = response_data.get('images', [])
            credits_remaining = response_data.get('credits_remaining', 'N/A')

            if images_data:
                files_to_send = []
                for img_info in images_data:
                    img_url = img_info.get('url')
                    if img_url:
                        try:
                            # Download image bytes
                            img_response = requests.get(img_url)
                            img_response.raise_for_status()
                            # Create a Discord File object from bytes
                            filename = img_url.split('/')[-1]
                            files_to_send.append(discord.File(io.BytesIO(img_response.content), filename=filename))
                        except requests.exceptions.RequestException as e:
                            print(f"[ERROR] Failed to download image {img_url}: {e}")
                            await interaction.followup.send(f"❌ Failed to download one or more images from `{img_url}`. Error: `{e}`", ephemeral=True)
                            continue # Try to send other images

                if files_to_send:
                    await interaction.followup.send(
                        f"✅ Generation successful! Credits remaining: `{credits_remaining}`\n"
                        f"Prompt: `{prompt}`\nModel: `{chosen_model_obj['name']}`",
                        files=files_to_send
                    )
                else:
                    await interaction.followup.send(
                        f"✅ Generation successful, but no images were returned or could be downloaded. "
                        f"Credits remaining: `{credits_remaining}`", ephemeral=True
                    )
            else:
                await interaction.followup.send(
                    f"✅ Generation successful, but no images were provided by the API. "
                    f"Credits remaining: `{credits_remaining}`", ephemeral=True
                )
        else:
            # Fallback for API success: false or no 'success' field
            error_message = response_data.get('error', 'Unknown API error.') if response_data else 'No response data.'
            await interaction.followup.send(f"❌ Generation failed: `{error_message}`", ephemeral=False)

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred during generation: `{e}`", ephemeral=False)
        print(f"[ERROR] Exception during /generate command: {e}")

# --- NEW FEATURE: /models command ---
@bot.tree.command(name="models", description="List all available V.Artemis AI models.")
async def list_models(interaction: discord.Interaction):
    """
    Lists all models available from the V.Artemis API, showing their name and image size.
    """
    await interaction.response.defer() # Acknowledge the command immediately

    try:
        headers = get_authenticated_headers()
        # Refresh cache just in case it's stale or was empty on startup
        global available_models_cache
        models_data = make_api_request('GET', 'models', headers)
        if models_data and models_data.get("models"):
            available_models_cache = models_data["models"]
        else:
            await interaction.followup.send("❌ Error: Could not fetch available models from the API.", ephemeral=True)
            return

        if not available_models_cache:
            await interaction.followup.send("ℹ️ No models currently available from the V.Artemis API.", ephemeral=True)
            return

        # Create an embed for better presentation
        embed = discord.Embed(
            title="✨ Available V.Artemis Models ✨",
            description="Here are the generative AI models you can use:",
            color=discord.Color.blue()
        )

        for model in available_models_cache:
            model_name = model.get('name', 'Unnamed Model')
            img_size = model.get('img_size', 'N/A')
            # You might extend your API to include a 'description' field for models
            # description = model.get('description', 'No additional description.') 
            embed.add_field(name=f"🎨 {model_name}", value=f"Image Size: `{img_size}px`", inline=False)
        
        embed.set_footer(text=f"Data fetched from {BASE_URL}")
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while fetching models: `{e}`", ephemeral=True)
        print(f"[ERROR] Exception during /models command: {e}")

# --- NEW FEATURE: /about command ---
@bot.tree.command(name="about", description="Get information about this V.Artemis Bot.")
async def about_bot(interaction: discord.Interaction):
    """
    Provides information about the bot, its purpose, and developer.
    """
    embed = discord.Embed(
        title="V.Artemis Discord Bot",
        description=(
            "This bot connects to the **V.Artemis generative AI API**, a framework by V.Labs.\n\n"
            "**Current Features:**\n"
            "- `/generate`: Create AI-generated images from text prompts.\n"
            "- `/models`: See a list of all available AI models.\n"
            "- `/about`: Get information about this bot."
        ),
        color=discord.Color.purple()
    )
    embed.add_field(name="API Endpoint", value=f"`{BASE_URL}`", inline=False)
    embed.add_field(name="Developer", value="V.Labs (a branch of Vel Ltd.)", inline=True)
    embed.add_field(name="Version", value="1.0 (Discord Bot adaptation)", inline=True)
    embed.set_footer(text="Designed for personal use only.")
    await interaction.response.send_message(embed=embed, ephemeral=True) # Ephemeral as it's private bot info

# --- NEW FEATURE: /credits command (with important note) ---
@bot.tree.command(name="credits", description="Check your remaining V.Artemis API credits.")
async def check_credits(interaction: discord.Interaction):
    """
    Attempts to check remaining V.Artemis API credits.
    NOTE: This requires a dedicated /credits or similar endpoint on your API.
    The original script only reports credits after image generation.
    """
    await interaction.response.defer(ephemeral=True) # Acknowledge privately

    try:
        headers = get_authenticated_headers()
        
        # --- IMPORTANT NOTE ON API ENDPOINT ---
        # The original V.Artemis example API only returns 'credits_remaining'
        # as part of the /generate response. It does NOT have a dedicated endpoint
        # like '/api/v1/credits' or '/api/v1/user_info' to query credits directly.
        #
        # For this command to work, your V.Artemis API server would need to be
        # extended to provide a dedicated endpoint for checking credits.
        #
        # Example if you add one (e.g., GET http://127.0.0.1:5000/api/v1/credits):
        credits_data = make_api_request('GET', 'credits', headers) # <--- THIS ENDPOINT LIKELY DOES NOT EXIST YET ON YOUR API
        #
        # If you DO add a /credits endpoint, it should return something like:
        # {"success": true, "credits_remaining": 12345}

        if credits_data and credits_data.get('success'):
            remaining = credits_data.get('credits_remaining', 'N/A')
            await interaction.followup.send(f"💰 You have `{remaining}` V.Artemis API credits remaining.", ephemeral=True)
        else:
            # This branch will likely be hit if the 'credits' endpoint doesn't exist or fails.
            error_message = credits_data.get('error', 'API did not return credit information.') if credits_data else 'No response data from API.'
            await interaction.followup.send(
                f"❌ Could not retrieve credit information: `{error_message}`\n"
                "**Note:** Your V.Artemis API may not have a dedicated `/credits` endpoint. "
                "Credits are currently only reported after image generation.", ephemeral=True
            )

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred while checking credits: `{e}`\n"
                                        "Please ensure the API server is running and has a `/credits` endpoint configured.", ephemeral=True)
        print(f"[ERROR] Exception during /credits command: {e}")


# --- Run the Bot ---
if __name__ == "__main__":
    if not ARTEMIS_API_KEY:
        print("ERROR: ARTEMIS_API_KEY environment variable not set.")
        print("Please set it before running the bot.")
        sys.exit(1)
    if not DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN environment variable not set.")
        print("Please set it before running the bot.")
        sys.exit(1)
    if not BASE_URL:
        print("ERROR: BASE_URL is not set. Please set it to your Artemis API server URL (e.g., http://127.0.0.1:5000/api/v1).")
        sys.exit(1)

    try:
        bot.run(DISCORD_TOKEN)
    except discord.LoginFailure:
        print("ERROR: Invalid Discord Bot Token. Please check your DISCORD_TOKEN environment variable.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
