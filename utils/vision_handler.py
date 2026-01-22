"""
Vision API handler for extracting TOC structure from PDF page images.
Uses OpenAI-compatible API with vision capabilities.
"""
import base64
import json
import logging
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletion
import httpx

logger = logging.getLogger(__name__)


def encode_image_to_base64(image_bytes: bytes) -> str:
    """Encode image bytes to base64 string."""
    return base64.b64encode(image_bytes).decode('utf-8')


def create_vision_message(image_base64: str, system_prompt: str) -> List[Dict[str, Any]]:
    """
    Create a message list for vision API request.

    Args:
        image_base64: base64 encoded PNG image
        system_prompt: system instruction

    Returns:
        List of messages in OpenAI format
    """
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{image_base64}",
                        "detail": "high"
                    }
                }
            ]
        }
    ]


def extract_toc_from_image(
    client: OpenAI,
    model: str,
    image_base64: str,
    system_prompt: str,
    max_tokens: int = 2000,
    temperature: float = 0.1
) -> Optional[List[Dict[str, int]]]:
    """
    Send image to vision API and parse JSON response.

    Args:
        client: OpenAI client instance
        model: model name
        image_base64: base64 encoded PNG image
        system_prompt: system instruction for extraction
        max_tokens: max tokens in response
        temperature: sampling temperature

    Returns:
        List of TOC entries as dicts, or None if extraction failed
    """
    messages = create_vision_message(image_base64, system_prompt)
    try:
        response: ChatCompletion = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        if not content:
            logger.warning("Empty response from vision API")
            return None

        # Parse JSON
        data = json.loads(content)
        # Expecting a JSON object with a key like "toc" or directly an array
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Look for common keys
            for key in ['toc', 'table_of_contents', 'entries', 'sections']:
                if key in data and isinstance(data[key], list):
                    return data[key]
            # If no known key, assume the dict values are lists
            for value in data.values():
                if isinstance(value, list):
                    return value
        logger.warning(f"Unexpected JSON structure: {data}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Vision API call failed: {e}")
        return None


def get_default_system_prompt() -> str:
    """Return the default system prompt for TOC extraction."""
    return (
        "You are an experienced librarian converting paper books to e-books. "
        "I will provide an image of a Table of Contents (ToC).\n\n"

        "**OUTPUT FORMAT:**\n"
        "Strictly a JSON list of objects: [{\"title\": \"string\", \"page\": int, \"level\": int}]\n\n"

        "**RULES TO FOLLOW:**\n"
        "1. **Cleaning Rule:** If a page number has special characters (e.g., '/12', '...12', 'xii', '(12)', '[12]'), "
        "extract only the integer. For Roman numerals, convert to Arabic numerals if possible.\n"

        "2. **Hierarchy Rule:** Determine the 'level' based on visual indentation:\n"
        "   - Level 1: Left-aligned (main chapters, parts, major sections)\n"
        "   - Level 2: Indented 1 level (subsections)\n"
        "   - Level 3: Indented 2 levels (sub-subsections)\n"
        "   - Level 4+: Further indentation levels\n"

        "3. **Missing Page Number Logic (CRITICAL):**\n"
        "   - If an entry has NO visible page number:\n"
        "     a. If it's a sub-entry (level > 1), use the page number from the nearest parent entry above\n"
        "     b. If it's a main entry (level = 1) without a page number, use the previous main entry's page number\n"
        "     c. If it's the first entry and has no page number, use page 1\n"
        "   - IMPORTANT: Never leave 'page' as null or empty. Always infer a reasonable page number.\n"

        "4. **Page Number Validation:**\n"
        "   - Page numbers should be positive integers\n"
        "   - Page numbers should generally increase (but small decreases are allowed for front matter)\n"
        "   - Ignore any footnotes, annotations, or supplementary text\n"

        "5. **Title Cleaning:**\n"
        "   - Remove any leading/trailing dots, dashes, or special characters\n"
        "   - Preserve colons, commas, and parentheses within the title\n"
        "   - Trim extra whitespace\n"

        "6. **Complex Layout Handling:**\n"
        "   - For dual-column layouts, process left column first, then right column\n"
        "   - For multi-page ToCs, treat each page as a continuation\n"
        "   - Maintain consistent hierarchy across pages\n\n"

        "**EXAMPLES:**\n"
        "Input: 'Chapter 1 ... 5' → Output: {\"title\": \"Chapter 1\", \"page\": 5, \"level\": 1}\n"
        "Input: '  1.1 Introduction ...' (no page) → Output: {\"title\": \"1.1 Introduction\", \"page\": 5, \"level\": 2} (using parent's page)\n"
        "Input: 'Appendix A / 105' → Output: {\"title\": \"Appendix A\", \"page\": 105, \"level\": 1}\n\n"

        "**FINAL INSTRUCTION:**\n"
        "Output ONLY the JSON list, no markdown, no explanations, no additional text."
    )


def create_openai_client(base_url: str, api_key: str) -> OpenAI:
    """
    Create an OpenAI client configured for the given base URL and API key.

    Args:
        base_url: API base URL (e.g., https://api.deepseek.com)
        api_key: API key

    Returns:
        OpenAI client instance
    """
    # Create a custom httpx client without proxies to avoid compatibility issues
    # Note: Don't set base_url or headers here - let OpenAI client handle them
    http_client = httpx.Client(timeout=httpx.Timeout(30.0))

    return OpenAI(
        base_url=base_url,
        api_key=api_key,
        http_client=http_client,
    )