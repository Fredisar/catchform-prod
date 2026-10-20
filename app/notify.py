"""Notifications e-mail des nouvelles soumissions, via l'API HTTP de Resend.

Désactivées tant que RESEND_API_KEY n'est pas défini. L'envoi part dans un
thread pour ne pas faire attendre le visiteur qui remplit le formulaire.
"""
import json
import threading
import urllib.request
from html import escape

from flask import current_app

from .utils import as_text

RESEND_URL = "https://api.resend.com/emails"


def build_html(form_name, fields, dashboard_url):
    """Corps HTML de l'e-mail ; tout contenu venant du visiteur est échappé."""
    rows = "".join(
        "<tr>"
        f"<td style='padding:6px 14px 6px 0;color:#64748b;vertical-align:top'><b>{escape(str(key))}</b></td>"
        f"<td style='padding:6px 0;white-space:pre-wrap'>{escape(as_text(value))}</td>"
        "</tr>"
        for key, value in fields.items()
    )
    return (
        "<div style='font-family:Arial,sans-serif;font-size:14px;color:#0f172a'>"
        f"<h2 style='margin:0 0 16px'>Nouvelle soumission : {escape(form_name)}</h2>"
        f"<table style='border-collapse:collapse'>{rows}</table>"
        f"<p style='margin-top:24px'><a href='{escape(dashboard_url)}'>Voir dans le tableau de bord</a></p>"
        "</div>"
    )


def send_submission_email(to, form_name, fields, subject, dashboard_url):
    """Planifie l'envoi. Retourne False si les notifications sont désactivées."""
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        return False

    message = {
        "from": current_app.config["MAIL_FROM"],
        "to": [to],
        "subject": subject or f"Nouvelle soumission — {form_name}",
        "html": build_html(form_name, fields, dashboard_url),
    }
    # « Répondre » dans la messagerie écrit directement au visiteur.
    visitor_email = fields.get("email")
    if isinstance(visitor_email, str) and "@" in visitor_email:
        message["reply_to"] = visitor_email.strip()

    threading.Thread(
        target=_post, args=(api_key, message, current_app.logger), daemon=True
    ).start()
    return True


def send_reset_email(to, reset_url):
    api_key = current_app.config.get("RESEND_API_KEY")
    if not api_key:
        return False
    message = {
        "from": current_app.config["MAIL_FROM"],
        "to": [to],
        "subject": "Réinitialisation de ton mot de passe CatchForm",
        "html": f"""
        <div style='font-family:Arial,sans-serif;font-size:14px;color:#0f172a'>
          <h2>Réinitialisation demandée</h2>
          <p>Tu as demandé à réinitialiser ton mot de passe CatchForm.</p>
          <p><a href="{escape(reset_url)}" style='display:inline-block;padding:10px 18px;background:#6366f1;color:#fff;text-decoration:none;border-radius:8px'>Réinitialiser mon mot de passe</a></p>
          <p style='color:#64748b;font-size:12px'>Lien valable 1 heure. Si tu n'es pas à l'origine de cette demande, ignore cet e-mail.</p>
          <p style='color:#64748b;font-size:12px'>{escape(reset_url)}</p>
        </div>
        """,
    }
    threading.Thread(target=_post, args=(api_key, message, current_app.logger), daemon=True).start()
    return True


def _post(api_key, message, logger):
    request = urllib.request.Request(
        RESEND_URL,
        data=json.dumps(message).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "CatchForm/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10):
            pass
    except Exception as exc:  # un e-mail raté ne doit jamais casser une soumission
        logger.warning("Échec de la notification e-mail : %s", exc)
