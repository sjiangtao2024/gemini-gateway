"""多模态功能测试"""
import pytest
import base64
from pathlib import Path

from app.routes.openai import _extract_image_from_content, ImageGenerationRequest


class TestVision:
    """测试图像理解功能"""
    
    def test_extract_text_only(self):
        """测试纯文本内容"""
        content = [{"type": "text", "text": "Hello"}]
        text, files = _extract_image_from_content(content)
        
        assert text == "Hello"
        assert files == []
    
    def test_extract_base64_image(self):
        """测试提取 base64 图片"""
        # 创建一个简单的 base64 图片
        image_data = b"fake-image-data"
        base64_str = base64.b64encode(image_data).decode()
        
        content = [
            {"type": "text", "text": "描述这张图"},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_str}"}}
        ]
        
        text, files = _extract_image_from_content(content)
        
        assert text == "描述这张图"
        assert len(files) == 1
        # 验证临时文件存在
        assert files[0].endswith('.png')
        
        # 清理
        for f in files:
            try:
                Path(f).unlink()
            except:
                pass
    
    def test_extract_multiple_images(self):
        """测试提取多张图片"""
        base64_str = base64.b64encode(b"image").decode()
        
        content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_str}"}},
            {"type": "image_url", "image_url": {"url": f"data:image/webp;base64,{base64_str}"}}
        ]
        
        text, files = _extract_image_from_content(content)
        
        assert len(files) == 2
        assert files[0].endswith('.jpeg') or files[0].endswith('.jpg')
        assert files[1].endswith('.webp')
        
        # 清理
        for f in files:
            try:
                Path(f).unlink()
            except:
                pass
    
    def test_extract_no_images(self):
        """测试没有图片的情况"""
        content = []
        text, files = _extract_image_from_content(content)
        
        assert text == ""
        assert files == []


class TestImageGeneration:
    """测试图像生成功能"""
    
    def test_image_request_model_defaults(self):
        """测试图像生成请求模型默认值"""
        req = ImageGenerationRequest(
            model="gemini-2.5-pro",
            prompt="a cat"
        )
        
        assert req.model == "gemini-2.5-pro"
        assert req.prompt == "a cat"
        assert req.n == 1
        assert req.size == "1024x1024"
        assert req.response_format == "b64_json"
    
    def test_image_request_model_custom(self):
        """测试自定义参数"""
        req = ImageGenerationRequest(
            model="dall-e-3",
            prompt="a dog",
            n=3,
            size="512x512",
            response_format="url"
        )
        
        assert req.model == "dall-e-3"
        assert req.prompt == "a dog"
        assert req.n == 3
        assert req.size == "512x512"
        assert req.response_format == "url"
    
    def test_image_request_validation(self):
        """测试参数验证"""
        # n 必须 >= 1
        with pytest.raises(ValueError):
            ImageGenerationRequest(
                model="test",
                prompt="test",
                n=0
            )
        
        # n 必须 <= 10
        with pytest.raises(ValueError):
            ImageGenerationRequest(
                model="test",
                prompt="test",
                n=11
            )


class TestFileUpload:
    """测试文件上传功能（基础测试）"""
    
    def test_file_import(self):
        """测试文件路由可导入"""
        from app.routes.files import router, configure
        assert router is not None
        assert configure is not None
