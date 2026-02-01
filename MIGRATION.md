# Migration Guide: Hugging Face → OpenRouter

This guide walks you through migrating the Smart Vision Guide application from Hugging Face API to OpenRouter API.

## Why Migrate?

OpenRouter provides:
- **Multi-model support**: Easy switching between different vision models
- **Better infrastructure**: More reliable API endpoints
- **Free tier**: Access to `allenai/molmo-2-8b:free` model
- **Unified interface**: Standardized chat completions API

## Prerequisites

1. **Obtain an OpenRouter API Key**
   - Visit https://openrouter.ai/keys
   - Create an account (if you don't have one)
   - Generate a new API key
   - Keep it secure - you'll need it for configuration

## Migration Steps

### 1. Update Environment Variables

Edit your `.env` file (or create one from `.env.example`):

```bash
# Remove old Hugging Face variables
# HF_TOKEN=...
# HF_MODEL=...

# Add new OpenRouter variables
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=allenai/molmo-2-8b:free

# Optional: For rankings on openrouter.ai
OPENROUTER_SITE_URL=https://yoursite.com
OPENROUTER_SITE_NAME=Smart Vision Guide
```

### 2. Update Dependencies (Raspberry Pi OS Buster 10)

If you're running on **Raspberry Pi OS Buster 10**, the dependencies have been updated for compatibility:

```bash
# Update to latest requirements
pip install -r requirements.txt
```

**Important Buster 10 Notes:**
- Uses `opencv-python-headless` instead of `opencv-python` for ARM compatibility
- `dlib` may require compilation - install system dependencies first:
  ```bash
  sudo apt-get update
  sudo apt-get install cmake build-essential libatlas-base-dev libopenblas-dev liblapack-dev
  ```

### 3. Test the Configuration

Verify your setup:

```bash
python config.py
```

You should see:
```
🔧 API Configuration:
  OpenRouter: ✓ Configured
  Model:      allenai/molmo-2-8b:free
```

### 4. Test Image Analysis

Run a quick test:

```python
from handlers.ai_handler import AIHandler
from PIL import Image
import io

# Create a test image
img = Image.new('RGB', (200, 200), color='blue')
buf = io.BytesIO()
img.save(buf, format='JPEG')

# Test the handler
handler = AIHandler()
result = handler.analyze_image(buf.getvalue(), mode='describe')
print(result)
```

## What Changed?

### API Structure

**Before (Hugging Face):**
```python
{
    "inputs": {
        "image": "data:image/jpeg;base64,...",
        "text": "prompt"
    },
    "parameters": {
        "max_new_tokens": 150
    }
}
```

**After (OpenRouter):**
```python
{
    "model": "allenai/molmo-2-8b:free",
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "prompt"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
        ]
    }],
    "max_tokens": 150
}
```

### Response Format

**Before:** `{"generated_text": "..."}`  
**After:** `{"choices": [{"message": {"content": "..."}}]}`

## Troubleshooting

### "OPENROUTER_API_KEY is missing"
- Make sure your `.env` file exists and contains `OPENROUTER_API_KEY=...`
- Check that the key is valid (no extra spaces)

### "Model is loading" or 503 errors
- The model may be warming up (especially for free tier)
- The handler will automatically retry with exponential backoff
- Wait 10-15 seconds and try again

### Slow responses on Raspberry Pi
- This is normal for Pi Zero 2W
- Image preprocessing happens locally (reduces upload size)
- Network timeouts are set to 45 seconds
- Consider using faster WiFi or Ethernet adapter

### dlib compilation fails on Buster 10
```bash
# Install all required system dependencies
sudo apt-get install cmake build-essential libatlas-base-dev \
  libopenblas-dev liblapack-dev python3-dev

# Try installing from piwheels (may have pre-built ARM wheels)
pip install dlib --index-url https://www.piwheels.org/simple
```

## Rollback (if needed)

If you need to revert to Hugging Face:

1. Check out the previous commit: `git checkout HEAD~1`
2. Restore your old `.env` with `HF_TOKEN`
3. Reinstall old dependencies: `pip install -r requirements.txt`

## Support

- **OpenRouter Docs**: https://openrouter.ai/docs
- **Model Info**: https://openrouter.ai/models/allenai/molmo-2-8b:free
- **Issues**: Report on the project repository
