"""
Azure Computer Vision handler for Smart Vision Guide.
Optimized for Raspberry Pi Zero 2W with retry logic, reduced payload, and fast fallbacks.
"""

import io
import time
import re
import requests
from PIL import Image
from config import (
    AZURE_VISION_ENDPOINT, AZURE_VISION_KEY,
    REQUEST_TIMEOUT, IMAGE_MAX_WIDTH, IMAGE_JPEG_QUALITY, SEARCH_OBJECTS,
    ENABLE_PREPROCESSING, RETRY_ATTEMPTS, RETRY_DELAY
)

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
    """Handler for image analysis using Azure Computer Vision REST API."""

    DESCRIBE_PATH = "/vision/v3.2/describe"
    ANALYZE_PATH = "/vision/v3.2/analyze"
    READ_PATH = "/vision/v3.2/read/analyze"

    def __init__(self, retry_attempts=RETRY_ATTEMPTS, retry_delay=RETRY_DELAY):
        if not AZURE_VISION_ENDPOINT or not AZURE_VISION_KEY:
            raise RuntimeError("AZURE_VISION_ENDPOINT or AZURE_VISION_KEY is missing in environment variables.")

        self.endpoint = AZURE_VISION_ENDPOINT.rstrip("/")
        self.headers = {
            "Ocp-Apim-Subscription-Key": AZURE_VISION_KEY,
            "Content-Type": "application/octet-stream"
        }
        self.poll_headers = {
            "Ocp-Apim-Subscription-Key": AZURE_VISION_KEY
        }

        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.last_successful_response = None
        self.quota_exhausted = False

        # Keep online requests bounded while allowing a longer fallback window.
        max_budget = float(REQUEST_TIMEOUT)
        self.total_budget = min(max_budget, 3.0)
        self.request_timeout = min(max_budget, 2.5)
        self.timeout_tuple = (self.request_timeout, self.request_timeout)
        self.read_poll_interval = 0.35

        self.session = requests.Session()

    def _build_url(self, path):
        return f"{self.endpoint}{path}"

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

    def _raise_for_status(self, response):
        status = response.status_code
        if status < 400:
            return

        msg = self._extract_error(response)
        msg_lower = (msg or "").lower()

        if status in (401, 403):
            raise AzureAPIError(
                "Online API authorization failed. Please check your Azure Vision key.",
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

    def _describe(self, image_bytes, timeout_seconds=None):
        url = self._build_url(self.DESCRIBE_PATH)
        params = {
            "maxCandidates": 1,
            "language": "en",
            "overload": "stream"
        }
        response = self.session.post(
            url,
            headers=self.headers,
            params=params,
            data=image_bytes,
            timeout=self._timeout_tuple(timeout_seconds)
        )
        self._raise_for_status(response)
        result = response.json()
        captions = result.get("description", {}).get("captions", [])
        if not captions:
            return ""
        return (captions[0].get("text") or "").strip()

    def _analyze_objects(self, image_bytes, timeout_seconds=None):
        url = self._build_url(self.ANALYZE_PATH)
        params = {
            "visualFeatures": "Objects",
            "language": "en"
        }
        response = self.session.post(
            url,
            headers=self.headers,
            params=params,
            data=image_bytes,
            timeout=self._timeout_tuple(timeout_seconds)
        )
        self._raise_for_status(response)
        result = response.json()
        return result.get("objects", [])

    def _read_text(self, image_bytes, budget_seconds=None, timeout_seconds=None):
        url = self._build_url(self.READ_PATH)
        params = {
            "language": "en"
        }

        budget = self.total_budget if budget_seconds is None else max(0.5, float(budget_seconds))
        timeout = self.request_timeout if timeout_seconds is None else max(0.5, float(timeout_seconds))
        timeout_tuple = self._timeout_tuple(timeout)
        deadline = time.time() + budget
        response = self.session.post(
            url,
            headers=self.headers,
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

    def _description_hints_currency(self, text):
        lowered = (text or "").lower()
        keywords = ["money", "cash", "banknote", "bill", "coin", "currency"]
        return any(k in lowered for k in keywords)

    def _objects_hint_currency(self, objects):
        names = []
        for obj in objects or []:
            name = (obj.get("object") or "").strip().lower()
            if name:
                names.append(name)
        currency_terms = {"money", "cash", "banknote", "bill", "coin", "currency"}
        return any(name in currency_terms for name in names)

    def _extract_ocr_text(self, result):
        lines = []
        analyze = result.get("analyzeResult", {})
        for page in analyze.get("readResults", []):
            for line in page.get("lines", []):
                value = (line.get("text") or "").strip()
                if value:
                    lines.append(value)
        return " ".join(lines)

    def _detect_currency_from_text(self, text):
        if not text:
            return None

        upper = text.upper()

        # Specific codes first
        code_patterns = [
            ("USD", [r"\bUSD\b", r"US\$", r"\bUNITED STATES\b", r"\bUS DOLLAR(S)?\b"]),
            ("EUR", [r"\bEUR\b", r"\bEURO(S)?\b", "\u20ac"]),
            ("GBP", [r"\bGBP\b", r"\bPOUND(S)?\b", "\u00a3", r"\bSTERLING\b"]),
            ("JPY", [r"\bJPY\b", r"\bYEN\b", "\u00a5"]),
            ("CNY", [r"\bCNY\b", r"\bRMB\b", r"\bYUAN\b"]),
            ("INR", [r"\bINR\b", r"\bRUPEE(S)?\b", "\u20b9"]),
            ("NPR", [r"\bNPR\b", r"\bNEPALI RUPEE(S)?\b", r"\bNEPAL RASTRA BANK\b", r"\bGOVERNMENT OF NEPAL\b", r"\bNEPAL\b", "\u0930\u0941"]),
            ("KRW", [r"\bKRW\b", r"\bWON\b", "\u20a9"]),
            ("AUD", [r"\bAUD\b", r"A\$"]),
            ("CAD", [r"\bCAD\b", r"C\$"]),
            ("NZD", [r"\bNZD\b", r"NZ\$"]),
            ("SGD", [r"\bSGD\b", r"S\$"]),
            ("HKD", [r"\bHKD\b", r"HK\$"]),
            ("CHF", [r"\bCHF\b", r"\bFRANC(S)?\b"]),
            ("BRL", [r"\bBRL\b", r"R\$"]),
            ("MXN", [r"\bMXN\b"]),
            ("RUB", [r"\bRUB\b", r"\bRUBLE(S)?\b", "\u20bd"]),
            ("TRY", [r"\bTRY\b", r"\bLIRA\b", "\u20ba"])
        ]

        for code, patterns in code_patterns:
            for pattern in patterns:
                if re.search(pattern, upper):
                    return code

        # Symbols with no clear code
        if "\u20ac" in text:
            return "EUR"
        if "\u00a3" in text:
            return "GBP"
        if "\u20b9" in text:
            return "INR"
        if "\u20a9" in text:
            return "KRW"
        if "\u0930\u0941" in text:
            return "NPR"
        if "\u20bd" in text:
            return "RUB"
        if "\u20ba" in text:
            return "TRY"
        if "\u00a5" in text:
            return "JPY"
        if "$" in text:
            return "USD"

        return None

    def _currency_note_from_ocr(self, image_bytes, budget_seconds, confirmed=False):
        try:
            result = self._read_text(
                image_bytes,
                budget_seconds=budget_seconds,
                timeout_seconds=min(self.request_timeout, budget_seconds)
            )
            ocr_text = self._extract_ocr_text(result)
            currency = self._detect_currency_from_text(ocr_text)
            if currency:
                return f"Currency detected: {currency}."
            if confirmed:
                return "Currency detected, type unclear."
        except Exception:
            return None
        return None

    def _shorten(self, text, max_chars=180):
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

    def _is_description_short(self, text):
        if not text:
            return True
        cleaned = " ".join(text.split())
        return len(cleaned) < 25 or len(cleaned.split()) < 4

    def _is_fallback_description(self, text):
        return text.startswith("I'm looking at the image, but I can't make out clear details.")

    def _merge_descriptions(self, primary, secondary, max_sentences=3):
        def split_sentences(value):
            value = value.strip()
            if not value:
                return []
            parts = re.split(r"(?<=[.!?])\s+", value)
            return [p for p in parts if p]

        combined = split_sentences(primary) + split_sentences(secondary)
        if not combined:
            return ""
        combined = combined[:max_sentences]
        return " ".join(combined)

    def _format_describe(self, text):
        text = (text or "").strip()
        if not text:
            return "I'm looking at the image, but I can't make out clear details."
        if not text.endswith((".", "!", "?")):
            text = f"{text}."
        return self._shorten(text, 180)

    def _format_ocr(self, result):
        lines = []
        analyze = result.get("analyzeResult", {})
        for page in analyze.get("readResults", []):
            for line in page.get("lines", []):
                value = (line.get("text") or "").strip()
                if value:
                    lines.append(value)

        if not lines:
            return "I don't see any readable text in this image."

        joined = " / ".join(lines)
        joined = self._shorten(joined, 200)
        return f"I can read: {joined}"

    def _format_search(self, objects, width, height=None, query=None):
        parsed = self._parse_objects(objects)
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
                if pos:
                    return f"Yes, I see {match['name']} on the {pos}."
                return f"Yes, I see {match['name']}."
            return f"No, I don't see {query}."

        interpreted = interpret_azure_objects(objects, width, height)
        if interpreted:
            return interpreted

        common = {item.lower() for item in SEARCH_OBJECTS}
        filtered = [obj for obj in parsed if obj["name_lower"] in common]
        if not filtered:
            return "I don't see common items."

        parts = []
        for obj in filtered[:5]:
            pos = self._position_label(obj["rect"], width)
            if pos:
                parts.append(f"{obj['name']} ({pos})")
            else:
                parts.append(obj["name"])
        return f"I can see: {', '.join(parts)}."

    def analyze_image(self, image_bytes, mode='describe', query=None, progress_callback=None, return_status=False):
        """
        Analyze an image using Azure Computer Vision.

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
                    start_time = time.time()
                    raw = self._describe(processed_bytes)
                    formatted = self._format_describe(raw)

                    desc_short = self._is_description_short(raw) or self._is_fallback_description(formatted)
                    objects = None
                    interpreted = ""

                    elapsed = time.time() - start_time
                    remaining = self.total_budget - elapsed

                    # If description is short, try local interpretation from objects.
                    if desc_short and remaining > 0.6:
                        objects = self._analyze_objects(
                            processed_bytes,
                            timeout_seconds=min(self.request_timeout, remaining)
                        )
                        interpreted = interpret_azure_objects(objects, width, _height)
                        if interpreted:
                            formatted = interpreted

                    # Optional currency check for describe mode (OCR preferred, objects as a hint).
                    currency_note = None
                    elapsed = time.time() - start_time
                    remaining = self.total_budget - elapsed

                    if remaining > 0.8:
                        if self._description_hints_currency(raw):
                            currency_note = self._currency_note_from_ocr(processed_bytes, remaining, confirmed=True)
                        else:
                            if remaining > 1.4:
                                if objects is None:
                                    objects = self._analyze_objects(
                                        processed_bytes,
                                        timeout_seconds=min(self.request_timeout, remaining)
                                    )
                                if self._objects_hint_currency(objects):
                                    remaining = self.total_budget - (time.time() - start_time)
                                    if remaining > 0.8:
                                        currency_note = self._currency_note_from_ocr(
                                            processed_bytes,
                                            remaining,
                                            confirmed=True
                                        )
                                    else:
                                        currency_note = "Currency detected, type unclear."

                    if currency_note:
                        formatted = f"{formatted} {currency_note}"

                    # If we didn't override with interpreted text, append a short interpreted add-on.
                    if not desc_short and not interpreted and objects is None and remaining > 0.8:
                        objects = self._analyze_objects(
                            processed_bytes,
                            timeout_seconds=min(self.request_timeout, remaining)
                        )
                        interpreted = interpret_azure_objects(objects, width, _height, max_sentences=1)

                    if not desc_short and interpreted:
                        formatted = self._merge_descriptions(formatted, interpreted, max_sentences=3)
                elif mode == 'ocr':
                    raw = self._read_text(processed_bytes)
                    formatted = self._format_ocr(raw)
                elif mode == 'search':
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
