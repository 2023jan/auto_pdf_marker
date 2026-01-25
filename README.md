# PDF自动书签生成器

一个基于Python的Streamlit应用，使用Vision AI（多模态LLM）自动从PDF页面提取目录(TOC)并嵌入书签。不使用传统OCR技术——利用支持视觉的模型理解复杂布局（双列、表格等）。

## 功能特点

- **视觉而非OCR**：将PDF页面渲染为高质量图像并发送给多模态LLM进行结构提取
- **复杂布局支持**：处理双列目录、表格和其他复杂布局
- **灵活的API**：兼容任何OpenAI兼容的API（DeepSeek、OpenRouter、本地端点等）
- **页码偏移调整**：校正前言页码与实际页码的差异
- **Streamlit界面**：用户友好的Web界面进行配置和处理
- **书签嵌入**：使用PyMuPDF直接将分层书签嵌入PDF

## 技术栈

- **前端**：Streamlit
- **PDF处理**：PyMuPDF (fitz) 用于渲染页面为图像和写入书签
- **视觉API**：OpenAI兼容客户端（兼容DeepSeek、OpenRouter、GPT‑4o、Gemini、Claude等）
- **图像处理**：Pillow（包含在PyMuPDF中）

## 安装

1. **克隆或下载**此仓库：
   ```bash
   git clone <repository-url>
   cd auto_pdf_marker
   ```

2. **创建虚拟环境**（推荐）：
   ```bash
   python -m venv .venv
   # Windows系统：
   .venv\Scripts\activate
   # macOS/Linux系统：
   source .venv/bin/activate
   ```

3. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

## 配置

### API要求

您需要通过OpenAI兼容的API访问**支持视觉功能**的多模态LLM。选项包括：

| 提供商 | 基础URL | 示例模型 | 备注 |
|--------|---------|----------|------|
| **DeepSeek** | `https://api.deepseek.com` | `deepseek-vl`, `deepseek-chat` | `deepseek-vl`支持视觉功能 |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `gpt-4o`, `gemini-flash`, `claude-3.5-sonnet` | 提供视觉模型 |
| **本地** | `http://localhost:1234/v1` | 任何支持视觉的本地模型 | LM Studio, Ollama等 |
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4-turbo` | 标准OpenAI API |

**您需要从所选提供商获取API密钥**。

### 环境设置

1. **准备API密钥**：从您选择的提供商获取API密钥
2. **确保有足够的信用额度/配额**：视觉请求（图像处理）消耗更多token

## 使用

### 运行应用

1. **启动Streamlit服务器**：
   ```bash
   streamlit run app.py
   ```

2. **在浏览器中打开**显示的URL（通常是`http://localhost:8501`）

### 逐步工作流程

1. **配置API设置**（侧边栏）：
   - **基础地址**：您的API端点（例如`https://api.deepseek.com`）
   - **API密钥**：您的API密钥（隐藏输入）
   - **模型名称**：支持视觉的模型（例如`deepseek-vl`, `gpt-4o`）

2. **上传PDF**：
   - 点击"选择PDF文件"或拖放PDF文件
   - 应用将显示总页数

3. **定义目录范围**：
   - **起始页码**：目录的起始页码（物理页码）
   - **结束页码**：目录的结束页码
   - **页码偏移量**：如果目录显示"第一章在第1页"，但实际是PDF的第15页，则输入14

4. **调整处理设置**（侧边栏，可选）：
   - **图像DPI**：更高的DPI提高文本清晰度但增加API负载大小（推荐300‑600）
   - **最大Token数**：LLM响应的最大token数（2000‑4000）
   - **温度**：较低的值（0.1‑0.3）产生更确定的JSON输出

5. **处理PDF**：
   - 点击"✨ 处理PDF"按钮
   - 观察进度条，每个页面被渲染并发送到视觉API
   - 在预览面板中查看提取的条目

6. **下载增强版PDF**：
   - 点击"下载带书签的PDF"保存处理后的文件
   - 新的PDF将包含与提取结构匹配的嵌套书签

## 文件结构

```
15_auto_pdf_marker/
├── app.py                    # 主Streamlit应用
├── requirements.txt          # Python依赖
├── README.md                # 英文文档（本文件）
├── README_CN.md             # 中文文档
├── utils/                   # 核心模块
│   ├── __init__.py
│   ├── pdf_handler.py       # PDF加载、渲染、书签写入
│   ├── vision_handler.py    # 图像编码、Vision API客户端、JSON解析
│   └── config_handler.py    # 配置保存和加载
└── test_integration.py      # 集成测试（可选）
```

## 配置持久化

应用现在支持保存和加载配置设置：

### 功能
- **自动加载**：应用启动时自动加载设置
- **一键保存**：使用"💾 保存配置"按钮保存所有当前设置
- **安全存储**：API密钥在保存前进行混淆处理（Base64编码）
- **轻松管理**：使用"🗑️ 清除配置"按钮清除已保存的配置

### 保存的设置
- **API配置**：基础地址、API密钥、模型名称
- **处理设置**：图像DPI、最大Token数、温度
- **配置文件**：保存为项目根目录下的`pdf_marker_config.json`

### 使用方法
1. **配置**：填写您的API设置和处理偏好
2. **保存**：点击侧边栏的"💾 保存配置"
3. **重启**：设置将在应用重启后保留
4. **更新**：修改设置并再次保存以更新

### 安全说明
- **本地存储**：配置本地存储在JSON文件中
- **基本混淆**：API密钥进行Base64编码（非加密）
- **建议**：不要将`pdf_marker_config.json`提交到版本控制

## 工作原理

1. **PDF → 图像转换**：使用PyMuPDF将每个选定的PDF页面渲染为高分辨率PNG图像
2. **视觉API调用**：图像进行base64编码并发送给支持视觉的LLM，附带结构化提示
3. **JSON提取**：LLM返回`{title, page, level}`对象的JSON列表
4. **页码调整**：提取的页码根据用户指定的偏移量进行调整
5. **书签注入**：调整后的目录使用PyMuPDF的`set_toc()`方法写入PDF
6. **下载**：增强版PDF返回给用户

## 故障排除

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| **API密钥不被接受** | 验证您的API密钥有效且具有视觉权限 |
| **找不到模型** | 确保您使用支持视觉的模型（例如`deepseek-vl`，而不是`deepseek-chat`） |
| **空响应** | 提高DPI以获得更清晰的图像；检查API日志中的错误 |
| **页码不正确** | 根据PDF的前言调整页码偏移量值 |
| **内存错误** | 降低DPI或减少同时处理的页面数量 |
| **配置无法保存** | 检查写入权限；确保在保存前提供了API密钥 |
| **配置无法加载** | 检查`pdf_marker_config.json`是否存在且为有效的JSON |
| **Streamlit崩溃** | 确保所有依赖已安装；检查Python版本（3.8+） |

### 错误消息

- **"No module named 'fitz'"**：重新安装PyMuPDF：`pip install --force-reinstall pymupdf`
- **OpenAI客户端错误**：确保使用`openai==1.50.2`（从1.51.0降级以获得兼容性）
- **JSON解析错误**：视觉API可能未返回有效的JSON；尝试不同的模型
- **"Could not delete temporary file"**：Windows文件锁定问题；应用将自动重试
- **配置文件错误**：如果损坏，删除`pdf_marker_config.json`并重新配置

## 性能考虑

- **API成本**：视觉请求比纯文本请求消耗更多token
- **处理时间**：每个页面需要一个API调用；处理10页≈10个请求
- **图像大小**：更高的DPI提高图像质量但也增加负载大小和成本
- **速率限制**：尊重您的API提供商的速率限制；如果需要，添加延迟

## 扩展应用

### 添加新的API提供商

应用使用标准的OpenAI客户端格式。要添加对其他提供商的支持：

1. 确保他们提供OpenAI兼容的端点
2. 在"基础地址"字段中使用他们的基础URL
3. 从他们的产品中选择支持视觉的模型

### 自定义提取提示

编辑`utils/vision_handler.py`中的`get_default_system_prompt()`函数以修改提取指令。

### 添加后处理

修改`utils/pdf_handler.py`中的`write_toc()`函数以添加自定义验证或过滤TOC条目。

### 自定义配置存储

配置系统可以扩展或修改：

1. **更改存储位置**：修改`utils/config_handler.py`中的`CONFIG_FILE`
2. **添加新设置**：扩展`save_config()`和`load_config()`函数
3. **增强安全性**：为API密钥实现适当的加密（不仅仅是Base64混淆）
4. **多配置文件**：扩展以支持多个配置配置文件

配置存储在`pdf_marker_config.json`中，结构如下：
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

## 限制

- **API依赖**：需要互联网连接和有效的API凭据
- **成本**：视觉API调用比纯文本请求更昂贵
- **准确性**：取决于视觉模型解析复杂布局的能力
- **页面范围**：大页面范围将导致许多API调用

## 许可证

本项目按原样提供，用于教育和个人使用。请尊重您选择的API提供商的服务条款。

## 支持

如有问题或疑问：
1. 查看上面的故障排除部分
2. 验证您的API配置
3. 确保您使用支持视觉的模型
4. 首先使用简单的PDF进行测试

---

**注意**：此工具仅供授权使用。请确保您有权修改您处理的PDF。