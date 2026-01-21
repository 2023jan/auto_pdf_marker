"""
PDF Auto-Bookmarker: Streamlit application for automatic TOC extraction using Vision API.
"""
import streamlit as st
import fitz
import tempfile
import os
import json
import logging
import time
from typing import List, Dict, Any
from utils import pdf_handler, vision_handler, config_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="PDF Auto-Bookmarker",
    page_icon="📚",
    layout="wide"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .stProgress .st-bo {
        background-color: #4CAF50;
    }
    .success-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .error-message {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# App title
st.title("📚 PDF Auto-Bookmarker")
st.markdown("""
Automatically extract Table of Contents from PDF pages using Vision AI and embed bookmarks.
**No OCR** – uses multimodal LLM to understand complex layouts (dual-column, tables, etc.).
""")

# Load saved configuration
config = config_handler.load_config()
default_config = config_handler.get_default_config()

# Sidebar configuration
st.sidebar.header("🔧 API Configuration")

# Configuration management buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    save_button = st.button("💾 Save Config", use_container_width=True)
with col2:
    clear_button = st.button("🗑️ Clear Config", use_container_width=True)

# Handle configuration actions after all inputs are defined
if clear_button:
    if config_handler.clear_config():
        st.sidebar.success("Configuration cleared!")
        st.rerun()
    else:
        st.sidebar.error("Failed to clear configuration")

st.sidebar.markdown("---")

# API Configuration inputs with loaded values
base_url = st.sidebar.text_input(
    "Base URL",
    value=config.get("base_url", default_config["base_url"]) if config else default_config["base_url"],
    help="OpenAI-compatible API endpoint (e.g., https://api.deepseek.com, https://openrouter.ai/api/v1)"
)
api_key = st.sidebar.text_input(
    "API Key",
    value=config.get("api_key", default_config["api_key"]) if config else default_config["api_key"],
    type="password",
    help="Your API key for the chosen provider"
)
model = st.sidebar.text_input(
    "Model Name",
    value=config.get("model", default_config["model"]) if config else default_config["model"],
    help="Vision-capable model (e.g., deepseek-vl, gpt-4o, gemini-flash)"
)

st.sidebar.header("⚙️ Processing Settings")
dpi = st.sidebar.slider(
    "Image DPI",
    min_value=150,
    max_value=600,
    value=config.get("dpi", default_config["dpi"]) if config else default_config["dpi"],
    step=50,
    help="Higher DPI improves text clarity but increases API payload size"
)
max_tokens = st.sidebar.number_input(
    "Max Tokens",
    min_value=500,
    max_value=4000,
    value=config.get("max_tokens", default_config["max_tokens"]) if config else default_config["max_tokens"],
    step=500,
    help="Maximum tokens for LLM response"
)
temperature = st.sidebar.slider(
    "Temperature",
    min_value=0.0,
    max_value=1.0,
    value=config.get("temperature", default_config["temperature"]) if config else default_config["temperature"],
    step=0.05,
    help="Lower temperature for more deterministic JSON output"
)

# Main content area
st.header("📄 Step 1: Upload PDF")
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"],
    help="Upload the PDF you want to add bookmarks to"
)

if uploaded_file is not None:
    # Save uploaded file to temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_path = tmp_file.name

    try:
        # Load PDF to get page count
        doc = pdf_handler.load_pdf(tmp_path)
        total_pages = pdf_handler.get_page_count(doc)
        st.success(f"Loaded PDF with {total_pages} pages")

        st.header("🎯 Step 2: Define Table of Contents Range")
        col1, col2, col3 = st.columns(3)
        with col1:
            start_page = st.number_input(
                "Start Page",
                min_value=1,
                max_value=total_pages,
                value=1,
                help="First page of the Table of Contents (physical page number)"
            )
        with col2:
            end_page = st.number_input(
                "End Page",
                min_value=1,
                max_value=total_pages,
                value=min(10, total_pages),
                help="Last page of the Table of Contents (physical page number)"
            )
        with col3:
            page_offset = st.number_input(
                "Page Offset",
                min_value=-1000,
                max_value=1000,
                value=0,
                help="If ToC says 'Chapter 1 is on page 1', but that's actually page 15 of the PDF, enter 14"
            )

        # Validate range
        if start_page > end_page:
            st.error("Start page must be less than or equal to end page")
        else:
            st.info(f"Will process pages {start_page} to {end_page} (zero‑based: {start_page-1} to {end_page-1})")

            st.header("🚀 Step 3: Extract and Apply Bookmarks")
            if st.button("✨ Process PDF", type="primary", use_container_width=True):
                if not api_key:
                    st.error("Please enter your API key in the sidebar")
                else:
                    # Initialize progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Initialize OpenAI client
                    status_text.text("Initializing API client...")
                    client = vision_handler.create_openai_client(base_url, api_key)
                    system_prompt = vision_handler.get_default_system_prompt()

                    all_entries = []
                    total_pages_to_process = end_page - start_page + 1

                    # Process each page in the range
                    for i, physical_page in enumerate(range(start_page, end_page + 1)):
                        zero_based_page = physical_page - 1  # PyMuPDF uses 0‑based indexing
                        progress = (i + 1) / total_pages_to_process
                        progress_bar.progress(progress)
                        status_text.text(f"Processing page {physical_page} of {end_page}...")

                        # Render page to image
                        try:
                            image_bytes = pdf_handler.render_page_to_image(doc, zero_based_page, dpi)
                        except Exception as e:
                            st.error(f"Failed to render page {physical_page}: {e}")
                            continue

                        # Encode to base64
                        image_b64 = vision_handler.encode_image_to_base64(image_bytes)

                        # Call vision API
                        status_text.text(f"Extracting structure from page {physical_page}...")
                        entries = vision_handler.extract_toc_from_image(
                            client=client,
                            model=model,
                            image_base64=image_b64,
                            system_prompt=system_prompt,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )

                        if entries:
                            all_entries.extend(entries)
                            st.write(f"✅ Page {physical_page}: extracted {len(entries)} entries")
                        else:
                            st.warning(f"⚠️ Page {physical_page}: no entries extracted")

                    # Update progress
                    progress_bar.progress(1.0)
                    status_text.text("Processing complete!")

                    # Show extraction summary
                    if all_entries:
                        st.success(f"Extracted {len(all_entries)} total entries")

                        # Display preview of entries
                        with st.expander("📋 Preview Extracted Entries", expanded=True):
                            st.json(all_entries[:10])  # Show first 10 entries
                            if len(all_entries) > 10:
                                st.caption(f"Showing 10 of {len(all_entries)} entries")

                        # Apply page offset and write TOC
                        status_text.text("Applying bookmarks to PDF...")
                        output_bytes = pdf_handler.write_toc(
                            doc=doc,
                            toc=all_entries,
                            page_offset=page_offset,
                            output_path=None
                        )

                        # Create download button
                        st.header("📥 Step 4: Download Enhanced PDF")
                        st.download_button(
                            label="Download PDF with Bookmarks",
                            data=output_bytes,
                            file_name=f"bookmarked_{uploaded_file.name}",
                            mime="application/pdf",
                            use_container_width=True
                        )

                        # Cleanup
                        try:
                            doc.close()
                        except:
                            pass
                        # Try to delete temp file with retries for Windows file lock issues
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                os.unlink(tmp_path)
                                break  # Success, exit loop
                            except Exception as cleanup_error:
                                if retry == max_retries - 1:
                                    logger.warning(f"Could not delete temporary file {tmp_path} after {max_retries} attempts: {cleanup_error}")
                                else:
                                    time.sleep(0.1)  # Short delay before retry
                        st.balloons()
                    else:
                        st.error("No bookmarks were extracted. Please check your PDF and API configuration.")
                        # Cleanup even when no entries extracted
                        try:
                            doc.close()
                        except:
                            pass
                        # Try to delete temp file with retries for Windows file lock issues
                        max_retries = 3
                        for retry in range(max_retries):
                            try:
                                os.unlink(tmp_path)
                                break  # Success, exit loop
                            except Exception as cleanup_error:
                                if retry == max_retries - 1:
                                    logger.warning(f"Could not delete temporary file {tmp_path} after {max_retries} attempts: {cleanup_error}")
                                else:
                                    time.sleep(0.1)  # Short delay before retry

    except Exception as e:
        st.error(f"Error processing PDF: {e}")
        logger.exception("PDF processing error")
        # Clean up resources
        try:
            if 'doc' in locals():
                doc.close()
        except:
            pass
        # Clean up temp file with retries for Windows file lock issues
        if 'tmp_path' in locals():
            max_retries = 3
            for retry in range(max_retries):
                try:
                    os.unlink(tmp_path)
                    break  # Success, exit loop
                except Exception as cleanup_error:
                    if retry == max_retries - 1:
                        logger.warning(f"Could not delete temporary file {tmp_path} after {max_retries} attempts: {cleanup_error}")
                    else:
                        time.sleep(0.1)  # Short delay before retry
else:
    st.info("👈 Please upload a PDF file to begin")

# Footer
st.markdown("---")
st.markdown("""
### How It Works
1. **Vision over OCR**: PDF pages are rendered as high‑quality images and sent to a multimodal LLM.
2. **Structure Extraction**: The LLM analyzes the layout and returns a structured JSON list of titles, pages, and hierarchy levels.
3. **Bookmark Injection**: Extracted page numbers are adjusted by the offset you provide, then written into the PDF as a nested table of contents.

### Supported Providers
- **DeepSeek**: `deepseek-chat` (text‑only) or `deepseek-vl` (vision)
- **OpenRouter**: Any vision‑capable model (GPT‑4o, Gemini Flash, Claude 3.5 Sonnet, etc.)
- **Local OpenAI‑compatible endpoints**: LM Studio, Ollama, etc.

### Tips
- For complex layouts (dual‑column, tables), use a vision‑capable model.
- Increase DPI if the text appears blurry in the images.
- The page offset is crucial for academic papers where the front matter (roman numerals) shifts page numbering.
""")

# Handle configuration saving (must be after all inputs are defined)
if save_button:
    if not api_key:
        st.sidebar.error("API Key is required to save configuration")
    else:
        success = config_handler.save_config(
            base_url=base_url,
            api_key=api_key,
            model=model,
            dpi=dpi,
            max_tokens=max_tokens,
            temperature=temperature
        )
        if success:
            st.sidebar.success("Configuration saved successfully!")
        else:
            st.sidebar.error("Failed to save configuration")

# Show configuration status in sidebar
st.sidebar.markdown("---")
st.sidebar.header("📋 Configuration Status")
if config_handler.config_exists():
    st.sidebar.success("✅ Configuration loaded")
    st.sidebar.caption(f"Model: {model}")
    st.sidebar.caption(f"Base URL: {base_url[:30]}..." if len(base_url) > 30 else f"Base URL: {base_url}")
else:
    st.sidebar.info("📝 No saved configuration")