import pytest
from app.routes.claude import (
    ClaudeRequest, ClaudeMessage,
    _claude_to_openai_messages,
    _openai_to_claude_response
)


class TestClaudeFormatConversion:
    """测试 Claude ↔ OpenAI 格式转换"""
    
    def test_claude_to_openai_basic(self):
        """测试基本消息转换"""
        req = ClaudeRequest(
            model="gemini-2.5-pro",
            messages=[
                ClaudeMessage(role="user", content="Hello!")
            ]
        )
        
        result = _claude_to_openai_messages(req)
        
        assert result == [{"role": "user", "content": "Hello!"}]
    
    def test_claude_to_openai_with_system(self):
        """测试带 system prompt 的转换"""
        req = ClaudeRequest(
            model="gemini-2.5-pro",
            messages=[
                ClaudeMessage(role="user", content="Hello!")
            ],
            system="You are helpful"
        )
        
        result = _claude_to_openai_messages(req)
        
        assert result == [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello!"}
        ]
    
    def test_claude_to_openai_multi_turn(self):
        """测试多轮对话转换"""
        req = ClaudeRequest(
            model="gemini-2.5-pro",
            messages=[
                ClaudeMessage(role="user", content="Hello"),
                ClaudeMessage(role="assistant", content="Hi there"),
                ClaudeMessage(role="user", content="How are you?")
            ]
        )
        
        result = _claude_to_openai_messages(req)
        
        assert result == [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
            {"role": "user", "content": "How are you?"}
        ]
    
    def test_openai_to_claude_basic(self):
        """测试基本响应转换"""
        openai_result = {
            "text": "Hello! How can I help?"
        }
        
        result = _openai_to_claude_response(openai_result, "gemini-2.5-pro")
        
        assert result.model == "gemini-2.5-pro"
        assert result.role == "assistant"
        assert len(result.content) == 1
        assert result.content[0].text == "Hello! How can I help?"
        assert result.content[0].type == "text"
        assert result.stop_reason == "end_turn"
        assert result.type == "message"
    
    def test_openai_to_claude_from_choices(self):
        """测试从 choices 格式转换"""
        openai_result = {
            "choices": [
                {"message": {"role": "assistant", "content": "Sure!"}}
            ]
        }
        
        result = _openai_to_claude_response(openai_result, "gpt-4o")
        
        assert result.model == "gpt-4o"
        assert result.content[0].text == "Sure!"
    
    def test_openai_to_claude_empty_result(self):
        """测试空结果处理"""
        openai_result = {}
        
        result = _openai_to_claude_response(openai_result, "test-model")
        
        assert result.content[0].text == ""
        assert result.model == "test-model"
