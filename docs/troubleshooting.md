# 故障排查

## 1. g4f Provider 不可用

**症状**: `/v1/models` 返回空列表或调用报 `provider_error`。

**排查步骤**:
1) 检查 `g4f.providers` 白名单是否正确（大小写需匹配）。
2) 访问 g4f `GET /v1/providers` 与 `GET /v1/providers/{id}` 确认 provider 在线。
3) 若 provider 需要 cookies/HAR，检查 `har_and_cookies/` 是否挂载且文件可读。
4) 若使用浏览器类 provider，确认容器内 Chrome/Chromium 可用且 `shm_size` 足够。

## 2. 图像生成失败

**症状**: `/v1/images` 返回 `image_not_supported`。

**排查步骤**:
1) 确认请求 `model` 匹配 `g4f.model_prefixes` 或 Gemini 可用模型。
2) 对 `response_format=url` 失败时尝试 `b64_json`。
3) 省略 `size` 或使用 `1024x1024` 进行回归测试。

## 3. Cookies/HAR 失效

**症状**: g4f provider 登录失效，或 Gemini 报 401/503。

**排查步骤**:
1) 重新获取 cookies/HAR，并替换 `har_and_cookies/` 中文件。
2) Gemini 的 `cookies/gemini.json` 需包含 `__Secure-1PSID` 与 `__Secure-1PSIDTS`。
3) 若频繁失效，使用独立浏览器会话重新登录获取。

## 4. 模型列表聚合失败

**症状**: `/v1/models` 长时间不更新或为空。

**排查步骤**:
1) 检查 g4f 基础地址是否可访问。
2) 暂时放宽 `g4f.model_prefixes`，确认是否因前缀过滤导致为空。
3) 查看网关日志中的聚合错误并重试。

## 5. SSE 流式中断

**症状**: 流式响应中断或卡住。

**排查步骤**:
1) 确认反向代理已关闭缓冲（Nginx `proxy_buffering off`）。
2) 检查客户端超时设置是否过低。
3) 在服务端启用 DEBUG 日志查看流式发送过程。
