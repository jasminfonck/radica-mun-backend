import smtplib
import ssl
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


def enviar_acuse_recepcion(
    destinatario: str,
    asunto: str,
    entidad_nombre: str,
) -> bool:
    if not settings.SMTP_HOST or not settings.SMTP_USER:
        logger.info("SMTP no configurado — acuse no enviado")
        return False

    remitente = settings.SMTP_FROM or settings.SMTP_USER

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Formulario recibido — {entidad_nombre}"
    msg["From"] = remitente
    msg["To"] = destinatario

    html = f"""
    <html>
    <body style="margin:0;padding:0;font-family:Arial,Helvetica,sans-serif;background:#f5f5f5">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td align="center" style="padding:32px 16px">
            <table width="600" cellpadding="0" cellspacing="0"
                   style="background:#fff;border-radius:8px;overflow:hidden;
                          box-shadow:0 2px 8px rgba(0,0,0,.08)">

              <!-- Header -->
              <tr>
                <td style="background:#1a237e;padding:28px 32px">
                  <p style="margin:0;color:#fff;font-size:20px;font-weight:bold">{entidad_nombre}</p>
                  <p style="margin:4px 0 0;color:rgba(255,255,255,.75);font-size:13px">
                    Sistema de radicación de comunicaciones
                  </p>
                </td>
              </tr>

              <!-- Ícono de confirmación -->
              <tr>
                <td align="center" style="padding:32px 32px 0">
                  <div style="width:64px;height:64px;border-radius:50%;
                              background:#e8f5e9;display:inline-block;
                              line-height:64px;text-align:center;font-size:36px">
                    ✅
                  </div>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:24px 32px 32px">
                  <h2 style="margin:0 0 12px;color:#1a237e;font-size:20px;text-align:center">
                    Su formulario ha sido recibido
                  </h2>

                  <table width="100%" cellpadding="0" cellspacing="0"
                         style="border:1px solid #e0e0e0;border-radius:6px;overflow:hidden;
                                margin-bottom:24px">
                    <tr>
                      <td style="padding:12px 16px;font-size:13px;color:#555;
                                 font-weight:bold;width:140px;background:#f5f7ff">
                        Asunto
                      </td>
                      <td style="padding:12px 16px;font-size:14px;color:#333">{asunto}</td>
                    </tr>
                  </table>

                  <div style="background:#fff8e1;border:1px solid #ffe082;border-radius:6px;
                              padding:16px 20px;margin-bottom:20px">
                    <p style="margin:0 0 6px;font-size:14px;color:#333;font-weight:bold">
                      ⏳ Próximo paso
                    </p>
                    <p style="margin:0;font-size:14px;color:#555;line-height:1.6">
                      En un plazo máximo de <strong>24 horas hábiles</strong> recibirá
                      a este mismo correo el <strong>número de radicado oficial</strong>
                      de su comunicación, con el que podrá hacer seguimiento del trámite.
                    </p>
                  </div>

                  <p style="margin:0;font-size:13px;color:#777;line-height:1.6">
                    Una vez radicado, su solicitud será atendida en el plazo establecido
                    por la ley (máximo <strong>15 días hábiles</strong> conforme a la
                    Ley 1437 de 2011).
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="background:#f5f5f5;padding:16px 32px;
                           font-size:11px;color:#999;border-top:1px solid #e0e0e0">
                  Este correo fue generado automáticamente por el sistema de radicación
                  de {entidad_nombre}. Por favor no responda a este mensaje.
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(remitente, destinatario, msg.as_string())
        logger.info("Acuse enviado a %s (%s)", destinatario, codigo)
        return True
    except Exception as exc:
        logger.warning("No se pudo enviar acuse a %s: %s", destinatario, exc)
        return False
