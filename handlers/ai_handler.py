"""
AI Handler for Smart Vision Guide.
Uses OpenRouter API (nvidia/nemotron-nano-12b-v2-vl:free) for scene description and Azure Computer Vision for OCR/Search.
Optimized for Raspberry Pi Zero 2W with retry logic, reduced payload, and fast fallbacks.
"""

import io
import time
import re
import base64
import requests
from PIL import Image
from config import (
    AZURE_VISION_ENDPOINT, AZURE_VISION_KEY,
    OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_API_URL,
    REQUEST_TIMEOUT, IMAGE_MAX_WIDTH, IMAGE_JPEG_QUALITY, SEARCH_OBJECTS,
    ENABLE_PREPROCESSING, RETRY_ATTEMPTS, RETRY_DELAY,
    VI_PRIORITY_ITEMS, VI_PRIORITY_ALL
)

# System prompt for OpenRouter scene description (blind assistance)
SCENE_DESCRIPTION_PROMPT = """You are an assistive AI helping a blind person understand their surroundings and walk safely.

First, identify the environment:
- Say if the person is in a room, road, street, corridor, shop, or outdoor area.

Then describe ONLY important things:
- Obstacles
- People
- Doors
- Stairs
- Vehicles
- Safe walking path

For each important object:
- Mention what it is
- Mention direction (ahead, left, right)
- Estimate distance using:
  - Very close (under 1 meter)
  - About 1 meter
  - About 2-3 meters
  - Far

Rules:
- Start with: "You are in a ..."
- Mention the most important or dangerous object first
- Keep response short and practical
- Maximum 2-3 sentences
- Ignore colors and unimportant details
- Focus on safety and navigation
"""


def interpret_azure_objects(objects_json, image_width, image_height, max_sentences=3):
    """
    Convert Azure object detections into short, spatially-aware sentences.
    Returns an empty string if nothing meaningful can be produced.
    """
    if not objects_json or not image_width or not image_height:
        return ""

    try:
        image_area = float(image_width * image_height)
    except Exception:
        return ""

    if image_area <= 0:
        return ""

    critical = {
        "person", "people", "door", "stairs", "staircase", "step", "steps", "curb",
        "edge", "wall", "window", "glass", "pole", "post", "sign", "stop sign",
        "traffic light", "vehicle", "car", "bus", "truck", "bicycle", "bike",
        "motorcycle", "train", "dog", "cat"
    }
    large_furniture = {
        "table", "chair", "bed", "sofa", "couch", "desk", "bench",
        "cabinet", "closet", "wardrobe", "refrigerator", "fridge",
        "sink", "toilet", "tv"
    }

    def priority_rank(name_lower):
        if name_lower in critical:
            return 0
        if name_lower in large_furniture:
            return 1
        return 2

    def position_label(rect):
        if not rect:
            return None
        try:
            x = float(rect.get("x", 0))
            w = float(rect.get("w", 0))
            center = x + (w / 2.0)
        except Exception:
            return None

        if center < image_width * 0.33:
            return "left"
        if center > image_width * 0.66:
            return "right"
        return "center"

    def distance_label(rect):
        if not rect:
            return None
        try:
            w = float(rect.get("w", 0))
            h = float(rect.get("h", 0))
        except Exception:
            return None
        if w <= 0 or h <= 0:
            return None
        ratio = (w * h) / image_area
        if ratio >= 0.20:
            return "very close, about 1 arm length (2-3 feet)"
        if ratio >= 0.07:
            return "close, about 2 arm lengths (4-6 feet)"
        return "farther, 3+ arm lengths (7+ feet)"

    def is_plural(name_lower):
        if name_lower in {"people", "stairs", "steps"}:
            return True
        return name_lower.endswith("s") and not name_lower.endswith("ss")

    def article_for(name_lower):
        return "an" if name_lower[:1] in {"a", "e", "i", "o", "u"} else "a"

    parsed = []
    for obj in objects_json:
        name = (obj.get("object") or "").strip()
        if not name:
            continue
        name_lower = name.lower()
        parsed.append({
            "name": name_lower,
            "display": name_lower,
            "confidence": float(obj.get("confidence", 0) or 0),
            "rect": obj.get("rectangle") or {}
        })

    if not parsed:
        return ""

    parsed.sort(key=lambda o: (priority_rank(o["name"]), -o["confidence"]))

    sentences = []
    seen = set()
    for obj in parsed:
        if obj["name"] in seen:
            continue
        seen.add(obj["name"])

        pos = position_label(obj["rect"])
        dist = distance_label(obj["rect"])

        if pos == "center":
            location = "in front of you"
        elif pos in {"left", "right"}:
            location = f"to your {pos}"
        else:
            location = "nearby"

        if is_plural(obj["name"]):
            sentence = f"There are {obj['display']} {location}"
        else:
            sentence = f"There is {article_for(obj['name'])} {obj['display']} {location}"

        if dist:
            sentence = f"{sentence}, {dist}."
        else:
            sentence = f"{sentence}."

        sentences.append(sentence)
        if len(sentences) >= max_sentences:
            break

    return " ".join(sentences)


class AzureAPIError(RuntimeError):
    def __init__(self, message, retryable=False, quota=False, auth=False):
        super().__init__(message)
        self.retryable = retryable
        self.quota = quota
        self.auth = auth


class AzureAIHandler:
    """Handler for image analysis using Azure AI Foundry (describe) and Azure Computer Vision (OCR/search)."""

    # Azure Computer Vision paths (for OCR and search)
    ANALYZE_PATH = "/vision/v3.2/analyze"
    READ_PATH = "/vision/v3.2/read/analyze"

    def __init__(self, retry_attempts=RETRY_ATTEMPTS, retry_delay=RETRY_DELAY):
        # Check OpenRouter configuration for describe mode
        self.openrouter_available = bool(OPENROUTER_API_KEY)
        if self.openrouter_available:
            self.openrouter_key = OPENROUTER_API_KEY
            self.openrouter_url = OPENROUTER_API_URL
            self.openrouter_model = OPENROUTER_MODEL
            print(f"OK: OpenRouter configured for scene description (Model: {OPENROUTER_MODEL})")
        else:
            print("WARN: OpenRouter not configured. Describe mode will use fallback.")

        # Check Azure Vision configuration for OCR/search
        self.vision_available = bool(AZURE_VISION_ENDPOINT and AZURE_VISION_KEY)
        if self.vision_available:
            self.vision_endpoint = AZURE_VISION_ENDPOINT.rstrip("/")
            self.vision_headers = {
                "Ocp-Apim-Subscription-Key": AZURE_VISION_KEY,
                "Content-Type": "application/octet-stream"
            }
            self.poll_headers = {
                "Ocp-Apim-Subscription-Key": AZURE_VISION_KEY
            }
            print("OK: Azure Computer Vision configured for OCR/search")
        else:
            print("WARN: Azure Computer Vision not configured. OCR/search will use offline fallback.")

        if not self.openrouter_available and not self.vision_available:
            raise RuntimeError("Neither OpenRouter nor Azure Computer Vision is configured. Please set environment variables.")

        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.last_successful_response = None
        self.quota_exhausted = False

        # Keep online requests bounded while allowing a longer fallback window.
        max_budget = float(REQUEST_TIMEOUT)
        self.total_budget = min(max_budget, 15.0)  # Increased for OpenAI
        self.request_timeout = min(max_budget, 12.0)  # Increased for OpenAI
        self.timeout_tuple = (self.request_timeout, self.request_timeout)
        self.read_poll_interval = 0.35

        self.session = requests.Session()

    def _build_vision_url(self, path):
        return f"{self.vision_endpoint}{path}"

    def _timeout_tuple(self, timeout_seconds=None):
        if not timeout_seconds:
            return self.timeout_tuple
        return (timeout_seconds, timeout_seconds)

    def _prepare_image(self, image_bytes):
        """
        Resize and compress image to reduce payload size for Pi Zero 2W.
        Returns (jpeg_bytes, width, height) for the processed image.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            width, height = img.size
            fmt = (img.format or "").upper()

            needs_resize = ENABLE_PREPROCESSING and IMAGE_MAX_WIDTH > 0 and width > IMAGE_MAX_WIDTH
            needs_convert = img.mode != "RGB"
            needs_jpeg = fmt != "JPEG"

            should_reencode = needs_resize or needs_convert or needs_jpeg or ENABLE_PREPROCESSING

            if not should_reencode:
                return image_bytes, width, height

            if needs_resize:
                ratio = IMAGE_MAX_WIDTH / float(width)
                new_height = int(float(height) * ratio)
                resample = Image.Resampling.LANCZOS if hasattr(Image, "Resampling") else Image.LANCZOS
                img = img.resize((IMAGE_MAX_WIDTH, new_height), resample)
                width, height = img.size

            if img.mode != "RGB":
                img = img.convert("RGB")

            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=IMAGE_JPEG_QUALITY)
            return buffer.getvalue(), width, height
        except Exception:
            return image_bytes, None, None

    def _extract_error(self, response):
        try:
            data = response.json()
        except Exception:
            return response.text or ""

        if isinstance(data, dict):
            err = data.get("error") or {}
            if isinstance(err, dict):
                msg = err.get("message") or err.get("code") or ""
                return msg
        return str(data)

    def _raise_for_status(self, response, is_openai=False):
        status = response.status_code
        if status < 400:
            return

        msg = self._extract_error(response)
        msg_lower = (msg or "").lower()

        if status in (401, 403):
            service = "OpenRouter" if is_openai else "Azure Vision"
            raise AzureAPIError(
                f"{service} authorization failed. Please check your API key.",
                retryable=False,
                auth=True
            )

        if status == 429:
            if any(k in msg_lower for k in ["quota", "credit", "billing", "exceed"]):
                raise AzureAPIError(
                    "Online quota is exhausted. Please update your Azure plan or key.",
                    retryable=False,
                    quota=True
                )
            raise AzureAPIError(
                "Online service is busy. Please try again.",
                retryable=True
            )

        if status >= 500:
            raise AzureAPIError("Online service error. Please try again.", retryable=True)

        raise AzureAPIError("Online request failed.", retryable=False)

    def _describe_with_openrouter(self, image_bytes, timeout_seconds=None):
        """Use OpenRouter API to describe the scene."""
        if not self.openrouter_available:
            raise AzureAPIError("OpenRouter not configured.", retryable=False)

        # Encode image to base64
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json"
        }

        # System prompt for the AI - must give ONLY the final answer
        system_prompt = """You are an assistant for blind people. Look at the image and give a SHORT description for navigation.

RESPOND ONLY WITH THE FINAL DESCRIPTION. Do NOT explain your thinking. Do NOT include any reasoning.

Format your response EXACTLY like this example:
"You are in a living room. There is a table about 1 meter ahead. A chair is to your left, about 2 meters away."

Rules:
- Start with "You are in a..." or "You are on a..."
- Mention obstacles with direction (ahead, left, right) and distance
- Maximum 2-3 short sentences
- Focus only on navigation and safety"""

        # User prompt with the image
        user_prompt = "Describe this scene for a blind person. Give ONLY the final description, no thinking or reasoning."

        # OpenRouter API payload - using system + user messages
        payload = {
            "model": self.openrouter_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 150,  # Shorter to force concise response
            "temperature": 0.3,  # Lower for more consistent output
            "reasoning": {"enabled": False}  # Explicitly disable reasoning mode
        }

        timeout = timeout_seconds or self.request_timeout

        response = self.session.post(
            self.openrouter_url,
            headers=headers,
            json=payload,
            timeout=(timeout, timeout)
        )
        
        print(f"📡 OpenRouter API status: {response.status_code}")
        
        self._raise_for_status(response, is_openai=True)

        result = response.json()

        # Extract the response from OpenRouter format
        choices = result.get("choices", [])
        if not choices:
            print(f"⚠️  OpenRouter returned no choices. Full response: {result}")
            raise AzureAPIError("OpenRouter returned no response choices.", retryable=True)

        message = choices[0].get("message", {})
        
        # Try to get content first, then fall back to reasoning field
        text = message.get("content", "") or ""
        text = text.strip()
        
        # If content is empty, check for reasoning (some models return text there)
        if not text:
            reasoning = message.get("reasoning", "") or ""
            reasoning = reasoning.strip()
            
            if reasoning:
                print(f"📝 Content empty, extracting from reasoning field...")
                
                # Try to find the actual scene description in the reasoning
                # Look for sentences that match our expected output format
                import re
                
                # Pattern 1: Find "You are in..." sentences
                you_are_matches = re.findall(r'(?:^|\. |"|\'|\n)(You are (?:in|on|at|near)[^.!?]+[.!?])', reasoning, re.IGNORECASE)
                
                if you_are_matches:
                    # Get the first "You are in..." and following sentences
                    start_idx = reasoning.lower().find(you_are_matches[0].lower())
                    if start_idx >= 0:
                        remaining = reasoning[start_idx:]
                        # Take up to 3 sentences
                        sentences = re.split(r'(?<=[.!?])\s+', remaining)
                        text = ' '.join(sentences[:3]).strip()
                
                # Pattern 2: Look for quoted final response
                if not text:
                    quoted = re.findall(r'"([^"]{20,200})"', reasoning)
                    for q in quoted:
                        if 'you are in' in q.lower() or 'you are on' in q.lower():
                            text = q.strip()
                            break
                
                # Pattern 3: Take the last paragraph if it looks like a description
                if not text:
                    paragraphs = [p.strip() for p in reasoning.split('\n\n') if p.strip()]
                    for para in reversed(paragraphs):
                        # Check if paragraph looks like a scene description
                        if ('you are' in para.lower() or 
                            'ahead' in para.lower() or 
                            'left' in para.lower() or 
                            'right' in para.lower()):
                            # Take first 2-3 sentences
                            sentences = re.split(r'(?<=[.!?])\s+', para)
                            text = ' '.join(sentences[:3]).strip()
                            break
                
                # Fallback: just take something reasonable from the reasoning
                if not text and len(reasoning) > 50:
                    # Take the last meaningful chunk, limited to reasonable TTS length
                    lines = [l.strip() for l in reasoning.split('\n') if l.strip()]
                    for line in reversed(lines):
                        if len(line) > 30 and len(line) < 300:
                            text = line
                            break
                    if not text:
                        text = reasoning[:250] + "..."
                
                print(f"📝 Extracted from reasoning: {text[:80]}...")
        
        if not text:
            print(f"⚠️  OpenRouter returned empty text. Message: {message}")
            raise AzureAPIError("OpenRouter returned empty text.", retryable=True)
        
        # Clean up the text - remove quotes if present
        text = text.strip('"').strip("'")

        # Check if the response indicates it couldn't process the image
        failure_phrases = [
            "i can't process",
            "i cannot process",
            "unable to process",
            "can't analyze",
            "cannot analyze",
            "unable to analyze",
            "i'm sorry, but i",
            "i'm unable to",
            "cannot identify",
            "can't identify",
            "i cannot see",
            "i can't see the image",
            "image is not clear",
            "image is too",
        ]
        text_lower = text.lower()
        for phrase in failure_phrases:
            if phrase in text_lower:
                print(f"⚠️  OpenRouter indicated failure: {text[:100]}")
                raise AzureAPIError(f"OpenRouter couldn't process: {text[:50]}", retryable=False)

        print(f"✓ OpenRouter response: {text[:100]}...")
        return text

    def _analyze_objects(self, image_bytes, timeout_seconds=None):
        """Use Azure Computer Vision to detect objects."""
        if not self.vision_available:
            return []

        url = self._build_vision_url(self.ANALYZE_PATH)
        params = {
            "visualFeatures": "Objects",
            "language": "en"
        }
        response = self.session.post(
            url,
            headers=self.vision_headers,
            params=params,
            data=image_bytes,
            timeout=self._timeout_tuple(timeout_seconds)
        )
        self._raise_for_status(response)
        result = response.json()
        return result.get("objects", [])

    def _read_text(self, image_bytes, budget_seconds=None, timeout_seconds=None):
        """Use Azure Computer Vision OCR to read text."""
        if not self.vision_available:
            raise AzureAPIError("Azure Computer Vision not configured for OCR.", retryable=False)

        url = self._build_vision_url(self.READ_PATH)
        params = {
            "language": "en"
        }

        budget = self.total_budget if budget_seconds is None else max(0.5, float(budget_seconds))
        timeout = self.request_timeout if timeout_seconds is None else max(0.5, float(timeout_seconds))
        timeout_tuple = self._timeout_tuple(timeout)
        deadline = time.time() + budget
        response = self.session.post(
            url,
            headers=self.vision_headers,
            params=params,
            data=image_bytes,
            timeout=timeout_tuple
        )
        self._raise_for_status(response)

        if response.status_code not in (200, 202):
            raise AzureAPIError("Online OCR request failed.", retryable=True)

        operation_location = response.headers.get("Operation-Location")
        if not operation_location:
            raise AzureAPIError("Online OCR response missing operation location.", retryable=True)

        while time.time() < deadline:
            poll = self.session.get(
                operation_location,
                headers=self.poll_headers,
                timeout=timeout_tuple
            )
            self._raise_for_status(poll)
            result = poll.json()
            status = (result.get("status") or "").lower()

            if status == "succeeded":
                return result
            if status == "failed":
                raise AzureAPIError("Online OCR failed.", retryable=False)

            time.sleep(self.read_poll_interval)

        raise AzureAPIError("Online OCR timed out.", retryable=True)

    def _shorten(self, text, max_chars=200):
        text = " ".join(text.split()).strip()
        if len(text) <= max_chars:
            return text
        cutoff = text.rfind(".", 0, max_chars)
        if cutoff > 40:
            return text[: cutoff + 1].strip()
        return text[:max_chars].rstrip(".") + "."

    def _position_label(self, rect, width):
        if not rect or not width:
            return None
        x = rect.get("x", 0)
        w = rect.get("w", 0)
        center = x + (w / 2.0)
        if center < width * 0.33:
            return "left"
        if center > width * 0.66:
            return "right"
        return "center"

    def _parse_objects(self, objects):
        parsed = []
        for obj in objects or []:
            name = (obj.get("object") or "").strip()
            if not name:
                continue
            parsed.append({
                "name": name,
                "name_lower": name.lower(),
                "confidence": float(obj.get("confidence", 0) or 0),
                "rect": obj.get("rectangle") or {}
            })
        parsed.sort(key=lambda o: o["confidence"], reverse=True)
        return parsed

    def _format_ocr(self, result):
        lines = []
        analyze = result.get("analyzeResult", {})
        for page in analyze.get("readResults", []):
            for line in page.get("lines", []):
                value = (line.get("text") or "").strip()
                if value:
                    # Clean up text for better TTS reading
                    # Remove or replace characters that sound awkward when spoken
                    cleaned = value
                    cleaned = cleaned.replace("/", " ")  # slash -> space
                    cleaned = cleaned.replace("\\", " ")  # backslash -> space
                    cleaned = cleaned.replace("|", " ")  # pipe -> space
                    cleaned = cleaned.replace("_", " ")  # underscore -> space
                    cleaned = cleaned.replace("@", " at ")  # @ -> at
                    cleaned = cleaned.replace("&", " and ")  # & -> and
                    cleaned = cleaned.replace("#", " number ")  # # -> number
                    cleaned = cleaned.replace("$", " dollars ")  # $ -> dollars
                    cleaned = cleaned.replace("%", " percent ")  # % -> percent
                    cleaned = " ".join(cleaned.split())  # normalize whitespace
                    if cleaned:
                        lines.append(cleaned)

        if not lines:
            return "I don't see any readable text in this image."

        # Join lines with periods for natural speech pauses
        joined = ". ".join(lines)
        # Ensure it ends with a period
        if not joined.endswith("."):
            joined += "."
        joined = self._shorten(joined, 250)
        return f"I can read: {joined}"

    def _distance_label(self, rect, image_area):
        """Calculate distance estimate based on object size in image."""
        if not rect or not image_area:
            return None
        try:
            w = float(rect.get("w", 0))
            h = float(rect.get("h", 0))
        except Exception:
            return None
        if w <= 0 or h <= 0:
            return None
        ratio = (w * h) / image_area
        if ratio >= 0.20:
            return "very close, about 1 arm length"
        if ratio >= 0.07:
            return "close, about 2 arm lengths"
        return "farther away, 3 or more arm lengths"

    def _get_priority(self, name_lower):
        """Get priority level for an item (0=high, 1=medium, 2=low, 3=none)."""
        for priority, (level, items) in enumerate(VI_PRIORITY_ITEMS.items()):
            if name_lower in [item.lower() for item in items]:
                return priority
        return 3  # Not a priority item

    def _format_search(self, objects, width, height=None, query=None):
        """Format search results with VI-priority item detection."""
        parsed = self._parse_objects(objects)
        image_area = (width * height) if width and height else None

        # If user specified a query, search for that specific item
        if query:
            q = query.strip().lower()
            if not q:
                return "I don't see the requested item."
            match = None
            for obj in parsed:
                name = obj["name_lower"]
                if q in name or name in q or q.rstrip("s") == name:
                    match = obj
                    break
            if match:
                pos = self._position_label(match["rect"], width)
                dist = self._distance_label(match["rect"], image_area)
                if pos and dist:
                    pos_text = "in front of you" if pos == "center" else f"to your {pos}"
                    return f"Yes, I found {match['name']} {pos_text}, {dist}."
                elif pos:
                    pos_text = "in front of you" if pos == "center" else f"to your {pos}"
                    return f"Yes, I found {match['name']} {pos_text}."
                return f"Yes, I see {match['name']}."
            return f"No, I don't see {query}."

        # No query - scan for VI-priority items
        if not parsed:
            return "I don't see any recognizable items."

        # Filter to VI-priority items and sort by priority
        vi_items = []
        for obj in parsed:
            priority = self._get_priority(obj["name_lower"])
            if priority < 3:  # Is a priority item
                vi_items.append((priority, obj))

        if not vi_items:
            # Fall back to general object interpretation
            interpreted = interpret_azure_objects(objects, width, height)
            if interpreted:
                return interpreted
            return "I don't see common items that visually impaired users typically need."

        # Sort by priority (high first), then by confidence
        vi_items.sort(key=lambda x: (x[0], -x[1]["confidence"]))

        # Build response grouped by position
        left_items = []
        center_items = []
        right_items = []

        seen = set()
        for priority, obj in vi_items:
            if obj["name_lower"] in seen:
                continue
            seen.add(obj["name_lower"])

            pos = self._position_label(obj["rect"], width)
            dist = self._distance_label(obj["rect"], image_area)
            item_desc = obj["name"]
            if dist:
                item_desc = f"{obj['name']}, {dist}"

            if pos == "left":
                left_items.append(item_desc)
            elif pos == "right":
                right_items.append(item_desc)
            else:
                center_items.append(item_desc)

            # Limit to 5 items total for clarity
            if len(seen) >= 5:
                break

        # Build natural response
        parts = []
        if center_items:
            items_text = ", ".join(center_items[:2])
            parts.append(f"In front of you: {items_text}")
        if left_items:
            items_text = ", ".join(left_items[:2])
            parts.append(f"To your left: {items_text}")
        if right_items:
            items_text = ", ".join(right_items[:2])
            parts.append(f"To your right: {items_text}")

        if not parts:
            return "I don't see common items."

        return ". ".join(parts) + "."

    def analyze_image(self, image_bytes, mode='describe', query=None, progress_callback=None, return_status=False):
        """
        Analyze an image using Azure OpenAI (describe) or Azure Computer Vision (OCR/search).

        Args:
            image_bytes: Raw image bytes
            mode: One of 'describe', 'ocr', 'search'
            query: Optional query for search mode
            progress_callback: Optional callback function for progress updates

        Returns:
            Human-readable analysis result
        """
        if self.quota_exhausted:
            msg = "Online quota is exhausted. Please update your Azure plan or key."
            return (False, msg) if return_status else msg

        processed_bytes, width, _height = self._prepare_image(image_bytes)

        for attempt in range(self.retry_attempts + 1):
            try:
                if progress_callback and attempt > 0:
                    progress_callback(f"Retry attempt {attempt}")

                if mode == 'describe':
                    # Use OpenRouter for scene description
                    if not self.openrouter_available:
                        msg = "OpenRouter is not configured for scene description."
                        return (False, msg) if return_status else msg
                    
                    formatted = self._describe_with_openrouter(processed_bytes)
                    formatted = self._shorten(formatted, 300)

                elif mode == 'ocr':
                    # Use Azure Computer Vision for OCR
                    if not self.vision_available:
                        msg = "Azure Computer Vision is not configured for text reading."
                        return (False, msg) if return_status else msg
                    
                    raw = self._read_text(processed_bytes)
                    formatted = self._format_ocr(raw)

                elif mode == 'search':
                    # Use Azure Computer Vision for object search
                    if not self.vision_available:
                        msg = "Azure Computer Vision is not configured for object search."
                        return (False, msg) if return_status else msg
                    
                    raw = self._analyze_objects(processed_bytes)
                    formatted = self._format_search(raw, width, _height, query=query)

                else:
                    formatted = "Unsupported mode."

                self.last_successful_response = formatted
                return (True, formatted) if return_status else formatted

            except AzureAPIError as e:
                if e.quota:
                    self.quota_exhausted = True
                if e.retryable and attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                msg = str(e)
                return (False, msg) if return_status else msg

            except requests.exceptions.Timeout:
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                msg = "The online analysis timed out. Please try again."
                return (False, msg) if return_status else msg

            except requests.exceptions.ConnectionError:
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                msg = "I couldn't connect to the online analysis service."
                return (False, msg) if return_status else msg

            except Exception:
                if attempt < self.retry_attempts:
                    time.sleep(self.retry_delay)
                    continue
                msg = "Sorry, I couldn't analyze the image right now."
                return (False, msg) if return_status else msg

        msg = "Analysis failed after multiple attempts."
        return (False, msg) if return_status else msg

    def quick_search(self, image_bytes, query, progress_callback=None):
        """Quick search for a specific object in the image."""
        return self.analyze_image(
            image_bytes,
            mode='search',
            query=query,
            progress_callback=progress_callback
        )


# Backwards-compatible alias used by main.py
AIHandler = AzureAIHandler
