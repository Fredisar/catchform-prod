"""Mon compte : changement e-mail/mdp, suppression, reset password."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from .extensions import db
from .models import User

account_bp = Blueprint("account", __name__)


@account_bp.route("/account", methods=["GET", "POST"])
@login_required
def account():
    if request.method == "POST":
        action = request.form.get("action")
        if action == "update_email":
            new_email = request.form.get("email", "").strip().lower()
            if "@" not in new_email or "." not in new_email.split("@")[-1]:
                flash("Adresse e-mail invalide.", "error")
            elif User.query.filter_by(email=new_email).first():
                flash("Cette adresse est déjà utilisée.", "error")
            elif new_email == current_user.email:
                flash("C'est déjà ton adresse.", "error")
            else:
                current_user.email = new_email
                db.session.commit()
                flash("Adresse e-mail mise à jour.", "success")
            return redirect(url_for("account.account"))

        if action == "update_password":
            current_pw = request.form.get("current_password", "")
            new_pw = request.form.get("new_password", "")
            if not current_user.check_password(current_pw):
                flash("Mot de passe actuel incorrect.", "error")
            elif len(new_pw) < 8:
                flash("Le nouveau mot de passe doit faire au moins 8 caractères.", "error")
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash("Mot de passe mis à jour.", "success")
            return redirect(url_for("account.account"))

        if action == "delete_account":
            # Double confirmation via case à cocher + mot de passe
            confirm = request.form.get("confirm_delete") == "on"
            pw = request.form.get("delete_password", "")
            if not confirm or not current_user.check_password(pw):
                flash("Confirmation invalide : coche la case et entre ton mot de passe.", "error")
                return redirect(url_for("account.account"))
            email = current_user.email
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            flash(f"Compte {email} supprimé — toutes tes données ont été effacées (RGPD).", "success")
            return redirect(url_for("public.index"))

    return render_template("account.html")


@account_bp.route("/reset-password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if user:
            token = user.get_reset_token()
            reset_url = url_for("account.reset_token", token=token, _external=True)
            # Si Resend configuré, envoie ; sinon affiche en flash pour dev
            from flask import current_app
            if current_app.config.get("RESEND_API_KEY"):
                try:
                    from .notify import send_reset_email
                    send_reset_email(user.email, reset_url)
                except Exception:
                    pass
            flash("Si ce compte existe, un e-mail de réinitialisation a été envoyé (lien valable 1h).", "success")
            # En dev sans e-mail, on expose le lien pour tester
            if not current_app.config.get("RESEND_API_KEY"):
                flash(f"Lien de réinitialisation (dev) : {reset_url}", "success")
        else:
            flash("Si ce compte existe, un e-mail a été envoyé.", "success")
        return redirect(url_for("auth.login"))
    return render_template("reset_request.html")


@account_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))
    user = User.verify_reset_token(token, max_age=3600)
    if not user:
        flash("Lien invalide ou expiré (1h). Refais une demande.", "error")
        return redirect(url_for("account.reset_request"))
    if request.method == "POST":
        pw = request.form.get("password", "")
        if len(pw) < 8:
            flash("Le mot de passe doit faire au moins 8 caractères.", "error")
        else:
            user.set_password(pw)
            db.session.commit()
            flash("Mot de passe réinitialisé — connecte-toi.", "success")
            return redirect(url_for("auth.login"))
    return render_template("reset_token.html", token=token)
