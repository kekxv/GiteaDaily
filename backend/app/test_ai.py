"""
测试 AI 服务功能。

主要测试：
1. 默认系统提示词是否正确设置
2. 返回内容验证
3. 错误处理
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai import AIService, DEFAULT_SUMMARY_PROMPT


class TestAIDefaultPrompt:
    """测试 AI 默认提示词"""

    def test_default_prompt_exists(self):
        """验证默认提示词存在且不为空"""
        assert DEFAULT_SUMMARY_PROMPT is not None
        assert len(DEFAULT_SUMMARY_PROMPT) > 100

    def test_default_prompt_contains_required_sections(self):
        """验证默认提示词包含必要的格式说明"""
        assert "今日工作摘要" in DEFAULT_SUMMARY_PROMPT
        assert "项目变更详情" in DEFAULT_SUMMARY_PROMPT
        assert "重点关注" in DEFAULT_SUMMARY_PROMPT
        assert "Markdown" in DEFAULT_SUMMARY_PROMPT or "markdown" in DEFAULT_SUMMARY_PROMPT

    def test_default_prompt_requests_chinese(self):
        """验证默认提示词要求使用中文回复"""
        assert "中文" in DEFAULT_SUMMARY_PROMPT


class TestAIServiceSummarize:
    """测试 AI 服务 summarize_report 方法"""

    @pytest.mark.asyncio
    async def test_uses_default_prompt_when_none_provided(self):
        """验证当未提供 system_prompt 时使用默认值"""
        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "### 工作摘要\n今日完成了测试。"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            # 验证调用时使用了默认提示词
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            system_message = messages[0]['content']
            assert system_message == DEFAULT_SUMMARY_PROMPT

    @pytest.mark.asyncio
    async def test_uses_custom_prompt_when_provided(self):
        """验证当提供自定义 system_prompt 时使用自定义值"""
        custom_prompt = "自定义提示词"

        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "测试结果"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content",
                system_prompt=custom_prompt
            )

            call_args = mock_client.chat.completions.create.call_args
            messages = call_args.kwargs['messages']
            system_message = messages[0]['content']
            assert system_message == custom_prompt

    @pytest.mark.asyncio
    async def test_returns_error_for_empty_response(self):
        """验证空响应返回错误信息"""
        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = ""
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            assert "空内容" in result

    @pytest.mark.asyncio
    async def test_returns_error_for_short_response(self):
        """验证过短响应返回错误信息"""
        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "短"  # 少于 20 字符
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            assert "过短" in result

    @pytest.mark.asyncio
    async def test_max_tokens_is_set(self):
        """验证 max_tokens 参数设置正确"""
        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "这是一个足够长的测试响应内容，超过20个字符。"
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            call_args = mock_client.chat.completions.create.call_args
            max_tokens = call_args.kwargs.get('max_tokens')
            assert max_tokens == 2000

    @pytest.mark.asyncio
    async def test_successful_response_is_returned(self):
        """验证成功响应被正确返回"""
        expected_content = """### 📊 今日工作摘要
今日完成了用户登录功能的开发。

### 📦 项目变更详情
- **user-service**: 实现了 OAuth2 登录
- **api-gateway**: 添加了认证中间件

### ⚠️ 重点关注
需要明天完成单元测试。"""

        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = expected_content
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="some git commits"
            )

            assert result == expected_content
            assert "今日工作摘要" in result


class TestAIErrorHandling:
    """测试 AI 服务错误处理"""

    @pytest.mark.asyncio
    async def test_handles_connection_error(self):
        """验证网络连接错误的处理"""
        import httpx

        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.chat.completions.create = AsyncMock(
                side_effect=httpx.ConnectError("Connection failed")
            )

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            assert "网络连接失败" in result or "出错" in result

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self):
        """验证超时错误的处理"""
        import httpx

        with patch('app.services.ai.AsyncOpenAI') as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            mock_client.chat.completions.create = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            result = await AIService.summarize_report(
                api_base="https://api.example.com/v1",
                api_key="test-key",
                model="gpt-3.5-turbo",
                content="test content"
            )

            assert "超时" in result or "出错" in result