import os
import sys
import json
import logging
import pytest
import fitz  # PyMuPDF
from unittest.mock import MagicMock, patch, mock_open
from typing import Dict, Any

# 确保可以导入 utils 模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import config_handler, pdf_handler, vision_handler

# 配置日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Fixtures (测试夹具) ---

@pytest.fixture
def temp_pdf_file(tmp_path):
    """创建一个简单的虚拟 PDF 用于测试。"""
    logger.info("创建临时 PDF 文件...")
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Hello World! This is page 1.")
    page = doc.new_page()
    page.insert_text((50, 50), "This is page 2.")
    
    pdf_path = tmp_path / "test.pdf"
    doc.save(pdf_path)
    doc.close()
    logger.info(f"临时 PDF 已保存至: {pdf_path}")
    return str(pdf_path)

@pytest.fixture
def mock_config_data():
    return {
        "base_url": "https://api.mock.com",
        "api_key": "sk-mock-key",
        "model": "mock-model",
        "dpi": 300,
        "max_tokens": 1000,
        "temperature": 0.5,
        "version": "1.0"
    }

# --- Config Handler Tests (配置处理测试) ---

def test_config_save_and_load(tmp_path, mock_config_data):
    """测试保存和加载配置。"""
    logger.info("开始测试配置保存与加载...")
    # 模拟模块中的 CONFIG_FILE 路径以使用临时文件
    with patch('utils.config_handler.CONFIG_FILE', str(tmp_path / "test_config.json")):
        # 1. 保存配置
        logger.info(f"正在保存配置到: {tmp_path / 'test_config.json'}")
        success = config_handler.save_config(
            base_url=mock_config_data["base_url"],
            api_key=mock_config_data["api_key"],
            model=mock_config_data["model"],
            dpi=mock_config_data["dpi"],
            max_tokens=mock_config_data["max_tokens"],
            temperature=mock_config_data["temperature"]
        )
        assert success is True
        assert os.path.exists(tmp_path / "test_config.json")
        logger.info("配置保存成功。")

        # 2. 加载配置
        logger.info("正在加载配置...")
        loaded_config = config_handler.load_config()
        assert loaded_config is not None
        assert loaded_config["base_url"] == mock_config_data["base_url"]
        # API 密钥应该被反混淆回原始值
        assert loaded_config["api_key"] == mock_config_data["api_key"] 
        assert loaded_config["model"] == mock_config_data["model"]
        logger.info("配置加载并验证成功。")

def test_obfuscation():
    """测试 API 密钥混淆功能是否按预期工作。"""
    logger.info("测试 API 密钥混淆...")
    original_key = "sk-secret-123"
    obfuscated = config_handler._obfuscate_api_key(original_key)
    logger.info(f"原始密钥: {original_key}, 混淆后: {obfuscated}")
    assert obfuscated != original_key
    assert config_handler._deobfuscate_api_key(obfuscated) == original_key
    logger.info("密钥混淆测试通过。")

def test_load_real_config_if_exists():
    """
    测试加载真实配置文件（如果存在）。
    这确保我们可以按要求读取实际的用户配置。
    """
    logger.info("检查是否存在真实配置文件...")
    if config_handler.config_exists():
        logger.info("发现真实配置文件，尝试加载...")
        config = config_handler.load_config()
        assert config is not None
        assert "base_url" in config
        assert "api_key" in config
        # 我们不会打印或断言实际值以保持其安全，仅验证结构
        assert isinstance(config["dpi"], int)
        logger.info("真实配置文件加载成功（内容已验证但未记录日志）。")
    else:
        logger.info("未找到真实配置文件，跳过此测试部分。")

# --- PDF Handler Tests (PDF 处理测试) ---

def test_pdf_load_and_count(temp_pdf_file):
    """测试加载 PDF 并计算页数。"""
    logger.info(f"测试 PDF 加载: {temp_pdf_file}")
    doc = pdf_handler.load_pdf(temp_pdf_file)
    assert doc is not None
    count = pdf_handler.get_page_count(doc)
    logger.info(f"PDF 页数: {count}")
    assert count == 2
    doc.close()
    logger.info("PDF 加载测试通过。")

def test_render_page_to_image(temp_pdf_file):
    """测试将页面渲染为图像字节。"""
    logger.info("测试 PDF 页面渲染...")
    doc = pdf_handler.load_pdf(temp_pdf_file)
    image_bytes = pdf_handler.render_page_to_image(doc, 0, dpi=72)
    assert isinstance(image_bytes, bytes)
    assert len(image_bytes) > 0
    # 检查 PNG 魔数
    assert image_bytes.startswith(b'\x89PNG')
    logger.info(f"成功渲染页面，图像大小: {len(image_bytes)} 字节")
    doc.close()

def test_write_toc(temp_pdf_file, tmp_path):
    """测试将目录 (TOC) 写入 PDF。"""
    logger.info("测试写入 PDF 目录...")
    doc = pdf_handler.load_pdf(temp_pdf_file)
    
    # 定义一个简单的目录结构
    toc_entries = [
        {"title": "Chapter 1", "page": 1, "level": 1},
        {"title": "Section 1.1", "page": 2, "level": 2}
    ]
    logger.info(f"待写入的目录条目: {toc_entries}")
    
    output_path = str(tmp_path / "output.pdf")
    pdf_handler.write_toc(doc, toc_entries, output_path=output_path)
    doc.close()
    
    # 验证目录是否已写入
    logger.info(f"验证输出文件: {output_path}")
    doc_out = fitz.open(output_path)
    toc_out = doc_out.get_toc()
    # PyMuPDF TOC 格式: [lvl, title, page]
    logger.info(f"读取回的目录: {toc_out}")
    assert len(toc_out) == 2
    assert toc_out[0] == [1, "Chapter 1", 1]
    assert toc_out[1] == [2, "Section 1.1", 2]
    doc_out.close()
    logger.info("目录写入测试通过。")

# --- Vision Handler Tests (视觉处理测试) ---

def test_encode_image():
    """测试 Base64 编码。"""
    logger.info("测试 Base64 图像编码...")
    data = b"fake_image_data"
    encoded = vision_handler.encode_image_to_base64(data)
    assert isinstance(encoded, str)
    # 检查是否可以解码回去
    import base64
    assert base64.b64decode(encoded) == data
    logger.info("编码测试通过。")

@patch('utils.vision_handler.OpenAI')
def test_extract_toc_from_image_mock(mock_openai_class):
    """
    使用模拟的 OpenAI API 响应测试 TOC 提取。
    这确保单元测试逻辑不需要真实的 API 密钥。
    """
    logger.info("测试 Vision API 提取（使用 Mock）...")
    # 设置模拟响应
    mock_client = MagicMock()
    mock_openai_class.return_value = mock_client
    
    mock_response_content = json.dumps([
        {"title": "Intro", "page": 5, "level": 1},
        {"title": "Methods", "page": 10, "level": 1}
    ])
    
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = mock_response_content
    mock_client.chat.completions.create.return_value = mock_completion
    
    # 调用函数
    result = vision_handler.extract_toc_from_image(
        client=mock_client,
        model="mock-model",
        image_base64="fake_base64",
        system_prompt="test prompt"
    )
    
    logger.info(f"Mock 提取结果: {result}")
    
    # 验证断言
    assert result is not None
    assert len(result) == 2
    assert result[0]["title"] == "Intro"
    assert result[0]["page"] == 5

    # 验证 API 是否使用正确的参数调用
    mock_client.chat.completions.create.assert_called_once()
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "mock-model"
    assert call_kwargs["response_format"] == {"type": "json_object"}
    logger.info("Vision API Mock 测试通过。")

def test_extract_toc_parsing_resilience():
    """测试 extract_toc 可以处理嵌套的 JSON 结构。"""
    logger.info("测试 JSON 解析鲁棒性...")
    # 有时 LLM 返回 {"toc": [...]} 而不是直接的 [...]
    
    mock_client = MagicMock()
    
    # 情况 1: 嵌套在 "toc" 下
    mock_content = json.dumps({
        "toc": [
            {"title": "Chapter 1", "page": 1, "level": 1}
        ]
    })
    
    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = mock_content
    mock_client.chat.completions.create.return_value = mock_completion
    
    result = vision_handler.extract_toc_from_image(
        client=mock_client, model="m", image_base64="b", system_prompt="s"
    )
    
    logger.info(f"解析嵌套 JSON 结果: {result}")
    
    assert result is not None
    assert len(result) == 1
    assert result[0]["title"] == "Chapter 1"
    logger.info("解析鲁棒性测试通过。")