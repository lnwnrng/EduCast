"""邮件发送服务 — 通过 Resend API 发送验证码邮件。"""

import logging

import httpx

from app.config import settings
from app.exceptions import ProviderException

logger = logging.getLogger(__name__)

_VERIFICATION_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>EduCast 验证码</title>
</head>
<body style="margin:0;padding:0;background:#f5f7fa;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <div style="max-width:480px;margin:40px auto;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.06);overflow:hidden;">
    <div style="background:linear-gradient(135deg,#1677ff 0%,#4096ff 100%);padding:28px 32px;text-align:center;">
      <h1 style="margin:0;color:#fff;font-size:24px;font-weight:600;">EduCast 课影</h1>
    </div>
    <div style="padding:32px;">
      <p style="margin:0 0 16px;color:#333;font-size:15px;">您好，</p>
      <p style="margin:0 0 24px;color:#333;font-size:15px;">您正在注册 EduCast 账号，请使用以下验证码完成验证：</p>
      <div style="background:#f0f5ff;border:1px solid #d6e4ff;border-radius:8px;padding:20px;text-align:center;margin:0 0 24px;">
        <span style="font-size:32px;font-weight:700;letter-spacing:8px;color:#1677ff;">{code}</span>
      </div>
      <p style="margin:0 0 8px;color:#666;font-size:13px;">⏱ 验证码有效期为 <strong>{expire_minutes}</strong> 分钟，请尽快完成验证。</p>
      <p style="margin:0;color:#999;font-size:13px;">如非本人操作，请忽略此邮件。</p>
    </div>
    <div style="background:#f5f7fa;padding:16px 32px;text-align:center;">
      <p style="margin:0;color:#bbb;font-size:12px;">© EduCast 课影 — 面向高校教学的智能视频生产平台</p>
    </div>
  </div>
</body>
</html>
"""


class EmailService:
    """通过 Resend HTTP API 发送邮件。"""

    RESEND_API_URL = "https://api.resend.com/emails"

    @staticmethod
    async def send_verification_code(email: str, code: str) -> None:
        """发送注册验证码邮件。

        Args:
            email: 目标邮箱地址。
            code: 6 位验证码明文。

        Raises:
            ProviderException: Resend API 调用失败时抛出。
        """
        if not settings.RESEND_API_KEY:
            logger.warning(
                "RESEND_API_KEY 未配置，验证码将仅打印到日志。验证码: %s -> %s",
                email,
                code,
            )
            return

        html = _VERIFICATION_EMAIL_TEMPLATE.format(
            code=code,
            expire_minutes=settings.VERIFICATION_CODE_EXPIRE_MINUTES,
        )

        payload = {
            "from": settings.EMAIL_FROM,
            "to": [email],
            "subject": "EduCast 注册验证码",
            "html": html,
        }
        headers = {
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    EmailService.RESEND_API_URL,
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.error("Resend API 返回错误: %s %s", e.response.status_code, e.response.text)
            raise ProviderException(
                message=f"邮件发送失败（HTTP {e.response.status_code}）",
                error_code="EMAIL_SEND_FAILED",
            ) from e
        except httpx.RequestError as e:
            logger.error("Resend API 请求失败: %s", e)
            raise ProviderException(
                message="邮件发送失败（网络错误）",
                error_code="EMAIL_SEND_FAILED",
            ) from e

        logger.info("验证码邮件已发送至 %s", email)
