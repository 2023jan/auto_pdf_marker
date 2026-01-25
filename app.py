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
    page_title="PDF自动书签生成器",
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
st.title("📚 PDF自动书签生成器")
st.markdown("""
使用Vision AI自动从PDF页面提取目录并嵌入书签。
**非OCR技术** – 使用多模态LLM理解复杂布局（双列、表格等）。
""")

# Load saved configuration
config = config_handler.load_config()
default_config = config_handler.get_default_config()

# Sidebar configuration
st.sidebar.header("🔧 API配置")

# Configuration management buttons
col1, col2 = st.sidebar.columns(2)
with col1:
    save_button = st.button("💾 保存配置", use_container_width=True)
with col2:
    clear_button = st.button("🗑️ 清除配置", use_container_width=True)

# Handle configuration actions after all inputs are defined
if clear_button:
    if config_handler.clear_config():
        st.sidebar.success("配置已清除!")
        st.rerun()
    else:
        st.sidebar.error("清除配置失败")

st.sidebar.markdown("---")

# API Configuration inputs with loaded values
base_url = st.sidebar.text_input(
    "API基础地址",
    value=config.get("base_url", default_config["base_url"]) if config else default_config["base_url"],
    help="OpenAI兼容的API端点 (例如 https://api.deepseek.com, https://openrouter.ai/api/v1)"
)
api_key = st.sidebar.text_input(
    "API密钥",
    value=config.get("api_key", default_config["api_key"]) if config else default_config["api_key"],
    type="password",
    help="所选服务提供商的API密钥"
)
model = st.sidebar.text_input(
    "模型名称",
    value=config.get("model", default_config["model"]) if config else default_config["model"],
    help="支持视觉功能的模型 (例如 deepseek-vl, gpt-4o, gemini-flash)"
)

st.sidebar.header("⚙️ 处理设置")
dpi = st.sidebar.slider(
    "图像DPI",
    min_value=150,
    max_value=600,
    value=config.get("dpi", default_config["dpi"]) if config else default_config["dpi"],
    step=50,
    help="更高的DPI提高文本清晰度但增加API负载大小"
)
max_tokens = st.sidebar.number_input(
    "最大Token数",
    min_value=500,
    max_value=4000,
    value=config.get("max_tokens", default_config["max_tokens"]) if config else default_config["max_tokens"],
    step=500,
    help="LLM响应的最大Token数"
)
temperature = st.sidebar.slider(
    "温度",
    min_value=0.0,
    max_value=1.0,
    value=config.get("temperature", default_config["temperature"]) if config else default_config["temperature"],
    step=0.05,
    help="较低的温度产生更确定的JSON输出"
)

# Main content area
st.header("📄 步骤 1: 上传PDF文件")
uploaded_file = st.file_uploader(
    "选择PDF文件",
    type=["pdf"],
    help="上传您要添加书签的PDF文件"
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
        st.success(f"已加载PDF，共 {total_pages} 页")

        st.header("🎯 步骤 2: 定义目录范围")
        col1, col2, col3 = st.columns(3)
        with col1:
            start_page = st.number_input(
                "起始页码",
                min_value=1,
                max_value=total_pages,
                value=1,
                help="目录的起始页码（物理页码）"
            )
        with col2:
            end_page = st.number_input(
                "结束页码",
                min_value=1,
                max_value=total_pages,
                value=min(10, total_pages),
                help="目录的结束页码（物理页码）"
            )
        with col3:
            page_offset = st.number_input(
                "页码偏移量",
                min_value=-1000,
                max_value=1000,
                value=0,
                help="如果目录显示'第一章在第1页'，但实际是PDF的第15页，则输入14"
            )

        # Validate range
        if start_page > end_page:
            st.error("起始页码必须小于或等于结束页码")
        else:
            st.info(f"将处理第{start_page}页到第{end_page}页 (零基索引: {start_page-1}到{end_page-1})")

            st.header("🚀 步骤 3: 提取并应用书签")
            if st.button("✨ 处理PDF", type="primary", use_container_width=True):
                if not api_key:
                    st.error("请在侧边栏输入API密钥")
                else:
                    # Initialize progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    # Initialize OpenAI client
                    status_text.text("正在初始化API客户端...")
                    client = vision_handler.create_openai_client(base_url, api_key)
                    system_prompt = vision_handler.get_default_system_prompt()

                    all_entries = []
                    total_pages_to_process = end_page - start_page + 1

                    # Process each page in the range
                    for i, physical_page in enumerate(range(start_page, end_page + 1)):
                        zero_based_page = physical_page - 1  # PyMuPDF uses 0‑based indexing
                        progress = (i + 1) / total_pages_to_process
                        progress_bar.progress(progress)
                        status_text.text(f"正在处理第{physical_page}页，共{end_page}页...")

                        # Render page to image
                        try:
                            image_bytes = pdf_handler.render_page_to_image(doc, zero_based_page, dpi)
                        except Exception as e:
                            st.error(f"渲染第{physical_page}页失败: {e}")
                            continue

                        # Encode to base64
                        image_b64 = vision_handler.encode_image_to_base64(image_bytes)

                        # Call vision API
                        status_text.text(f"正在从第{physical_page}页提取结构...")
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
                            st.write(f"✅ 第{physical_page}页: 提取了{len(entries)}个条目")
                        else:
                            st.warning(f"⚠️ 第{physical_page}页: 未提取到条目")

                    # Update progress
                    progress_bar.progress(1.0)
                    status_text.text("处理完成！")

                    # Show extraction summary
                    if all_entries:
                        st.success(f"总共提取了{len(all_entries)}个条目")

                        # Display preview of entries
                        with st.expander("📋 预览提取的条目", expanded=True):
                            st.json(all_entries[:10])  # Show first 10 entries
                            if len(all_entries) > 10:
                                st.caption(f"显示前10个条目，共{len(all_entries)}个")

                        # Apply page offset and write TOC
                        status_text.text("正在将书签应用到PDF...")
                        output_bytes = pdf_handler.write_toc(
                            doc=doc,
                            toc=all_entries,
                            page_offset=page_offset,
                            output_path=None
                        )

                        # Create download button
                        st.header("📥 步骤 4: 下载增强版PDF")
                        st.download_button(
                            label="下载带书签的PDF",
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
                        st.error("未提取到书签。请检查您的PDF文件和API配置。")
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
        st.error(f"处理PDF时发生错误: {e}")
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
    st.info("👈 请上传一个PDF文件开始")

# Footer
st.markdown("---")
st.markdown("""
### 工作原理
1. **视觉而非OCR**: PDF页面被渲染为高质量图像并发送给多模态LLM。
2. **结构提取**: LLM分析布局并返回结构化的JSON列表，包含标题、页码和层级。
3. **书签注入**: 提取的页码根据您提供的偏移量进行调整，然后作为嵌套目录写入PDF。

### 支持的提供商
- **DeepSeek**: `deepseek-chat` (仅文本) 或 `deepseek-vl` (视觉)
- **OpenRouter**: 任何支持视觉的模型 (GPT‑4o, Gemini Flash, Claude 3.5 Sonnet等)
- **本地OpenAI兼容端点**: LM Studio, Ollama等

### 使用技巧
- 对于复杂布局(双列、表格)，请使用支持视觉的模型。
- 如果图像中的文本模糊，请提高DPI。
- 对于学术论文，页码偏移量至关重要，因为前言(罗马数字)会影响页码编号。
""")

# Handle configuration saving (must be after all inputs are defined)
if save_button:
    if not api_key:
        st.sidebar.error("保存配置需要API密钥")
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
            st.sidebar.success("配置保存成功！")
        else:
            st.sidebar.error("保存配置失败")

# Show configuration status in sidebar
st.sidebar.markdown("---")
st.sidebar.header("📋 配置状态")
if config_handler.config_exists():
    st.sidebar.success("✅ 配置已加载")
    st.sidebar.caption(f"模型: {model}")
    st.sidebar.caption(f"基础地址: {base_url[:30]}..." if len(base_url) > 30 else f"基础地址: {base_url}")
else:
    st.sidebar.info("📝 无保存的配置")