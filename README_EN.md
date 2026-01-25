# PDF Auto-Bookmarker

A Python-based Streamlit application that automatically extracts Table of Contents (TOC) from PDF pages using Vision AI (multimodal LLM) and embeds bookmarks into the PDF. No traditional OCR used—leverages vision-capable models to understand complex layouts (dual-column, tables, etc.).

## Features

- **Vision over OCR**: Renders PDF pages as high‑quality images and sends them to a multimodal LLM for structure extraction
- **Complex Layout Support**: Handles dual‑column tables of contents, tables, and other complex layouts
- **Flexible API**: Compatible with any OpenAI‑compatible API (DeepSeek, OpenRouter, local endpoints)
- **Page Offset Adjustment**: Corrects for front‑matter page numbering differences
- **Streamlit UI**: User‑friendly web interface for configuration and processing
- **Bookmark Injection**: Embeds hierarchical bookmarks directly into the PDF using PyMuPDF

## Technology Stack

- **Frontend**: Streamlit
- **PDF Processing**: PyMuPDF (fitz) for rendering pages to images and writing bookmarks
- **Vision API**: OpenAI‑compatible client (compatible with DeepSeek, OpenRouter, GPT‑4o, Gemini, Claude, etc.)
- **Image Processing**: Pillow (included with PyMuPDF)

## Installation

1. **Clone or download** this repository:
   ```bash
   git clone <repository-url>
   cd auto_pdf_marker
   ```

2. **Create a virtual environment** (recommended):
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On macOS/Linux:
   source .venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### API Requirements

You need access to a **vision‑capable** multimodal LLM through an OpenAI‑compatible API. Options include:

| Provider | Base URL | Example Models | Notes |
|----------|----------|----------------|-------|
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-vl`, `deepseek-chat` | `deepseek-vl` supports vision |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `gpt-4o`, `gemini-flash`, `claude-3.5-sonnet` | Vision models available |
| **Local** | `http://localhost:1234/v1` | Any local model with vision support | LM Studio, Ollama, etc. |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4-turbo` | Standard OpenAI API |

**You will need an API key** from your chosen provider.

### Environment Setup

1. **Prepare your API key** from your chosen provider.
2. **Ensure you have sufficient credits/quota** for vision requests (image processing consumes more tokens).

## Usage

### Running the Application

1. **Start the Streamlit server**:
   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`).

### Step‑by‑Step Workflow

1. **Configure API Settings** (sidebar):
   - **Base URL**: Your API endpoint (e.g., `https://api.deepseek.com`)
   - **API Key**: Your API key (hidden input)
   - **Model Name**: Vision‑capable model (e.g., `deepseek-vl`, `gpt-4o`)

2. **Upload PDF**:
   - Click "Browse files" or drag‑and‑drop your PDF
   - The application will show the total page count

3. **Define TOC Range**:
   - **Start Page**: First page of the Table of Contents (physical page number)
   - **End Page**: Last page of the Table of Contents
   - **Page Offset**: If the ToC says "Chapter 1 is on page 1", but that's actually page 15 of the PDF, enter 14

4. **Adjust Processing Settings** (sidebar, optional):
   - **Image DPI**: Higher DPI improves text clarity but increases API payload size (300‑600 recommended)
   - **Max Tokens**: Maximum tokens for LLM response (2000‑4000)
   - **Temperature**: Lower values (0.1‑0.3) for more deterministic JSON output

5. **Process PDF**:
   - Click the "✨ Process PDF" button
   - Watch the progress bar as each page is rendered and sent to the vision API
   - View extracted entries in the preview panel

6. **Download Enhanced PDF**:
   - Click "Download PDF with Bookmarks" to save the processed file
   - The new PDF will contain nested bookmarks matching the extracted structure

## File Structure

```
15_auto_pdf_marker/
├── app.py                    # Main Streamlit application
├── requirements.txt          # Python dependencies
├── README.md                # This file
├── utils/                   # Core modules
│   ├── __init__.py
│   ├── pdf_handler.py       # PDF loading, rendering, bookmark writing
│   ├── vision_handler.py    # Image encoding, Vision API client, JSON parsing
│   └── config_handler.py    # Configuration saving and loading
└── test_integration.py      # Integration tests (optional)
```

## Configuration Persistence

The application now supports saving and loading configuration settings:

### Features
- **Auto-load**: Settings are automatically loaded on app startup
- **One-click save**: Save all current settings with the "💾 Save Config" button
- **Secure storage**: API keys are obfuscated (Base64 encoded) before saving
- **Easy management**: Clear saved configuration with "🗑️ Clear Config" button

### Saved Settings
- **API Configuration**: Base URL, API Key, Model Name
- **Processing Settings**: Image DPI, Max Tokens, Temperature
- **Configuration File**: Saved as `pdf_marker_config.json` in the project root

### How to Use
1. **Configure**: Fill in your API settings and processing preferences
2. **Save**: Click "💾 Save Config" in the sidebar
3. **Restart**: Settings will persist across app restarts
4. **Update**: Modify settings and save again to update

### Security Notes
- **Local storage**: Configuration is stored locally in a JSON file
- **Basic obfuscation**: API keys are Base64 encoded (not encrypted)
- **Recommendation**: Do not commit `pdf_marker_config.json` to version control

## How It Works

1. **PDF → Image Conversion**: Each selected PDF page is rendered to a high‑resolution PNG image using PyMuPDF
2. **Vision API Call**: The image is base64‑encoded and sent to the vision‑capable LLM with a structured prompt
3. **JSON Extraction**: The LLM returns a JSON list of `{title, page, level}` objects
4. **Page Number Adjustment**: Extracted page numbers are adjusted by the user‑specified offset
5. **Bookmark Injection**: The adjusted TOC is written into the PDF using PyMuPDF's `set_toc()` method
6. **Download**: The enhanced PDF is returned to the user

## System Prompt

The application uses the following system prompt for structure extraction:

```
You are a structure extraction assistant. I will provide an image of a book's Table of Contents. It might be dual-column or complex. Output strictly a JSON list of objects: [{"title": "Section Name", "page": 123, "level": 1}]. 'page' is the page number printed in the image. 'level' is the hierarchy (1 for chapter, 2 for section). Do not output markdown, just the JSON string.
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **API key not accepted** | Verify your API key is valid and has vision permissions |
| **Model not found** | Ensure you're using a vision‑capable model (e.g., `deepseek-vl`, not `deepseek-chat`) |
| **Empty response** | Increase DPI for clearer images; check API logs for errors |
| **Incorrect page numbers** | Adjust the Page Offset value based on your PDF's front matter |
| **Memory errors** | Reduce DPI or process fewer pages at once |
| **Configuration not saving** | Check write permissions; ensure API key is provided before saving |
| **Configuration not loading** | Check if `pdf_marker_config.json` exists and is valid JSON |
| **Streamlit crashes** | Ensure all dependencies are installed; check Python version (3.8+) |

### Error Messages

- **"No module named 'fitz'"**: Reinstall PyMuPDF: `pip install --force-reinstall pymupdf`
- **OpenAI client errors**: Ensure you're using `openai==1.50.2` (downgraded from 1.51.0 for compatibility)
- **JSON parsing errors**: The vision API might not be returning valid JSON; try a different model
- **"Could not delete temporary file"**: Windows file locking issue; the app will retry automatically
- **Configuration file errors**: Delete `pdf_marker_config.json` and reconfigure if corrupted

## Performance Considerations

- **API Costs**: Vision requests consume more tokens than text‑only requests
- **Processing Time**: Each page requires an API call; processing 10 pages = ~10 requests
- **Image Size**: Higher DPI increases image quality but also payload size and cost
- **Rate Limits**: Respect your API provider's rate limits; add delays if needed

## Extending the Application

### Adding New API Providers

The application uses the standard OpenAI client format. To add support for other providers:

1. Ensure they offer an OpenAI‑compatible endpoint
2. Use their base URL in the "Base URL" field
3. Select a vision‑capable model from their offerings

### Customizing the Extraction Prompt

Edit `utils/vision_handler.py`, `get_default_system_prompt()` function to modify the extraction instructions.

### Adding Post‑Processing

Modify `utils/pdf_handler.py`, `write_toc()` function to add custom validation or filtering of TOC entries.

### Customizing Configuration Storage

The configuration system can be extended or modified:

1. **Change Storage Location**: Modify `CONFIG_FILE` in `utils/config_handler.py`
2. **Add New Settings**: Extend `save_config()` and `load_config()` functions
3. **Enhanced Security**: Implement proper encryption for API keys (not just Base64 obfuscation)
4. **Multiple Profiles**: Extend to support multiple configuration profiles

Configuration is stored in `pdf_marker_config.json` with the following structure:
```json
{
  "base_url": "https://api.deepseek.com",
  "api_key": "base64_encoded_api_key",
  "model": "deepseek-vl",
  "dpi": 300,
  "max_tokens": 2000,
  "temperature": 0.1,
  "version": "1.0"
}
```

## Limitations

- **API Dependency**: Requires internet connection and valid API credentials
- **Cost**: Vision API calls are more expensive than text‑only requests
- **Accuracy**: Depends on the vision model's ability to parse complex layouts
- **Page Range**: Large page ranges will result in many API calls

## License

This project is provided as-is for educational and personal use. Please respect the terms of service of your chosen API provider.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Verify your API configuration
3. Ensure you're using a vision‑capable model
4. Test with a simple PDF first

---

**Note**: This tool is for authorized use only. Always ensure you have the right to modify the PDFs you process.