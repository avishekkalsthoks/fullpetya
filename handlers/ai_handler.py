"""
AI Handler for Smart Vision Guide
Optimized for Raspberry Pi Zero 2W with retry logic, reduced payload, and progress feedback.
"""

import requests
import base64
import io
import time
from PIL import Image
from config import (
    OPENROUTER_API_KEY, OPENROUTER_API_URL, OPENROUTER_MODEL,
    OPENROUTER_SITE_URL, OPENROUTER_SITE_NAME,
    REQUEST_TIMEOUT, IMAGE_MAX_WIDTH, IMAGE_JPEG_QUALITY, SEARCH_OBJECTS
)


class AIHandler:
    """Handler for AI image analysis using OpenRouter API with Pi Zero optimizations."""
    
    def __init__(self, retry_attempts=2, retry_delay=2.0):
        """
        Initialize AI handler.
        
        Args:
            retry_attempts: Number of retry attempts for failed API calls
            retry_delay: Delay between retries in seconds
        """
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY is missing in environment variables.")
        
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Add optional site tracking headers for OpenRouter rankings
        if OPENROUTER_SITE_URL:
            self.headers["HTTP-Referer"] = OPENROUTER_SITE_URL
        if OPENROUTER_SITE_NAME:
            self.headers["X-Title"] = OPENROUTER_SITE_NAME
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.last_successful_response = None  # Cache for fallback

    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        Resize and compress image to reduce payload size for Pi Zero 2 W compatibility.
        
        Optimizations:
        - Reduced max width from 640 to match camera output
        - Quality reduced to minimize upload size
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            
            # Resize if width exceeds max
            if img.width > IMAGE_MAX_WIDTH:
                ratio = IMAGE_MAX_WIDTH / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((IMAGE_MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            # Convert to RGB if necessary (e.g. if RGBA)
            if img.mode != 'RGB':
                img = img.convert('RGB')
                
            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=IMAGE_JPEG_QUALITY)
            compressed = buffer.getvalue()
            
            print(f"✓ Image preprocessed: {len(image_bytes)} → {len(compressed)} bytes")
            return compressed
            
        except Exception as e:
            print(f"Error during image preprocessing: {e}")
            return image_bytes

    def _build_payload(self, image_bytes: bytes, mode: str, query: str = None) -> dict:
        """
        Build the API payload based on the analysis mode.
        
        Args:
            image_bytes: Raw image bytes
            mode: One of 'describe', 'ocr', 'search'
            query: Optional query for search mode
        """
        processed_bytes = self._preprocess_image(image_bytes)
        b64_image = base64.b64encode(processed_bytes).decode('utf-8')
        data_url = f"data:image/jpeg;base64,{b64_image}"
        
        # Enhanced prompts for better assistive experience
        prompts = {
            'describe': (
                "You are helping a blind person. Describe this image concisely. "
                "Focus on: main subject, what's happening, location/setting, "
                "important objects, colors, and spatial relationships. "
                "Keep it brief - 2 to 3 sentences maximum. Describe:"
            ),
            'ocr': (
                "You are reading text for a visually impaired person. "
                "Extract ONLY the visible text in this image. "
                "Preserve layout if it's a menu or sign. "
                "If no text, say 'No text detected.' Read:"
            ),
            'search': (
                f"You are helping a blind person find things. "
                f"Look at this image and identify objects you see. "
                f"Common items: {', '.join(SEARCH_OBJECTS[:12])}. "
                f"List main objects clearly and briefly. What's in this image:"
            )
        }
        
        prompt = prompts.get(mode, prompts['describe'])
        
        # Add query context for search mode
        if mode == 'search' and query:
            prompt = (
                f"You are helping a blind person search for '{query}'. "
                f"Look carefully. If you see '{query}' or something similar, "
                f"confirm it clearly and describe its location. "
                f"If not present, briefly say what you do see. "
                f"Is '{query}' in this image:"
            )
        
        # OpenRouter chat completions format with image_url
        return {
            "model": OPENROUTER_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": data_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 150,
            "temperature": 0.7
        }

    def analyze_image(self, image_bytes: bytes, mode: str = 'describe', query: str = None, progress_callback=None) -> str:
        """
        Sends image to OpenRouter API and returns the generated text.
        
        Args:
            image_bytes: Raw image bytes
            mode: One of 'describe', 'ocr', 'search'
            query: Optional query for search mode
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Human-readable analysis result
        """
        payload = self._build_payload(image_bytes, mode, query)
        
        # Try with retry logic
        for attempt in range(self.retry_attempts + 1):
            try:
                if progress_callback and attempt > 0:
                    progress_callback(f"Retry attempt {attempt}")
                
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=REQUEST_TIMEOUT
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    print(f"Rate limited. Waiting {self.retry_delay * 2}s...")
                    time.sleep(self.retry_delay * 2)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                # Parse OpenRouter Response
                generated_text = None
                
                # OpenRouter format: {"choices": [{"message": {"content": "..."}}]}
                if isinstance(result, dict) and "choices" in result:
                    if len(result["choices"]) > 0 and "message" in result["choices"][0]:
                        generated_text = result["choices"][0]["message"].get("content", "")
                # Error message format
                elif isinstance(result, dict) and "error" in result:
                    error_msg = result.get("error", {}).get("message", "Unknown error")
                    print(f"API error response: {error_msg}")
                    if "loading" in error_msg.lower() or "warming up" in error_msg.lower():
                        print("Model is loading, will retry...")
                        time.sleep(self.retry_delay * 3)
                        continue
                    raise RuntimeError(f"API error: {error_msg}")
                else:
                    print(f"Unexpected response format: {result}")
                    if attempt < self.retry_attempts:
                        time.sleep(self.retry_delay)
                        continue
                    return "I'm sorry, I couldn't understand the response from the analysis service."
                
                # Clean up and format the response
                formatted = self._format_response(generated_text, mode, query)
                self.last_successful_response = formatted  # Cache for fallback
                return formatted
                    
            except requests.exceptions.Timeout:
                print(f"Request timed out (attempt {attempt + 1}/{self.retry_attempts + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                # Return cached response if available
                if self.last_successful_response:
                    return "The analysis is taking too long. Here's what I saw last time: " + self.last_successful_response
                return "The analysis timed out. Please check your internet connection and try again."
                
            except requests.exceptions.ConnectionError:
                print(f"Connection error (attempt {attempt + 1}/{self.retry_attempts + 1})")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                return "I couldn't connect to the analysis service. Please check your internet connection."
                
            except Exception as e:
                print(f"API Error (attempt {attempt + 1}/{self.retry_attempts + 1}): {e}")
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                return "Sorry, I couldn't analyze the image right now. Please try again."
        
        return "Analysis failed after multiple attempts. Please try again later."
    
    def _format_response(self, text: str, mode: str, query: str = None) -> str:
        """
        Format the AI response for better user experience.
        
        Args:
            text: Raw generated text
            mode: Analysis mode
            query: Optional search query
            
        Returns:
            Formatted, user-friendly response
        """
        # Clean up the text
        text = text.strip()
        
        # Remove common AI prefixes
        prefixes_to_remove = [
            "This image shows",
            "In this image",
            "I can see",
            "The image shows",
            "Looking at this image",
            "The image depicts",
            "This picture shows"
        ]
        
        for prefix in prefixes_to_remove:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()
                if text.startswith(","):
                    text = text[1:].strip()
                break
        
        # Mode-specific formatting
        if mode == 'describe':
            if not text or len(text) < 10:
                return "I'm looking at the image, but I can't make out clear details."
            return text
            
        elif mode == 'ocr':
            if not text or text.strip().lower() in ['no text detected', 'no text', 'no readable text']:
                return "I don't see any readable text in this image."
            return f"I can read: {text}"
            
        elif mode == 'search':
            if query:
                # Check if the response indicates the query was found
                positive_indicators = ['yes', 'i can see', 'there is', 'i see', 'found', 'visible']
                negative_indicators = ['no', "i don't see", 'not visible', 'cannot see', "isn't", 'not present']
                
                text_lower = text.lower()
                
                # Check for positive match
                has_positive = any(ind in text_lower for ind in positive_indicators)
                has_negative = any(ind in text_lower for ind in negative_indicators)
                
                if has_positive and not has_negative:
                    return f"Yes, I can see {query}."
                elif has_negative:
                    return f"No, I don't see {query} here."
                else:
                    return f"Looking for {query}. {text}"
            else:
                # General object listing
                if not text or len(text) < 5:
                    return "I'm looking around, but I can't identify specific objects clearly."
                return f"I can see: {text}"
        
        return text
    
    def quick_search(self, image_bytes: bytes, query: str, progress_callback=None) -> str:
        """
        Quick search for a specific object in the image.
        
        Args:
            image_bytes: Raw image bytes
            query: Object to search for
            progress_callback: Optional callback for progress updates
            
        Returns:
            Simple yes/no response with context
        """
        return self.analyze_image(image_bytes, mode='search', query=query, progress_callback=progress_callback)
