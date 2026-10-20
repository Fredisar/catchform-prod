"""App factory CatchForm."""
import click
from flask import Flask, render_template, request, g
from flask_wtf.csrf import CSRFError
from werkzeug.middleware.proxy_fix import ProxyFix

from .extensions import csrf, db, limiter, login_manager, migrate
from .utils import as_text


def create_app(config_object="config.Config"):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Derrière le proxy HTTPS de l'hébergeur : on respecte X-Forwarded-For/Proto
    # pour que les URLs d'endpoint générées soient bien en https://.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    # Désactive le rate limiting en mode test (évite les conflits avec le mock Thread de test_email_notification)
    if app.config.get("TESTING"):
        limiter.enabled = False

    from . import models  # noqa: F401  (enregistre les tables + le user_loader)
    from .auth import auth_bp
    from .dashboard import dashboard_bp
    from .ingest import ingest_bp
    from .public import public_bp
    from .account import account_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(ingest_bp)
    app.register_blueprint(account_bp)
    # L'endpoint public reçoit des POST depuis des sites tiers : pas de CSRF.
    csrf.exempt(ingest_bp)

    app.add_template_filter(as_text, "as_text")
    _register_error_handlers(app)
    _register_security_headers(app)
    _register_cli(app)

    # Migrations : en prod/dev on passe par `flask db upgrade`.
    # En TESTING (pytest, SQLite :memory:), on crée les tables à la volée
    # pour ne pas dépendre des fichiers de migration.
    if app.config.get("TESTING"):
        with app.app_context():
            db.create_all()

    return app


def _register_security_headers(app):
    @app.after_request
    def add_security_headers(response):
        # Ne pas polluer les réponses JSON de l'endpoint avec trop de headers stricts
        # mais appliquer quand même le minimum
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        # CSP souple : autorise self + inline styles (notre CSS), images/data, fonts self
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'"
        )
        # HSTS uniquement en prod HTTPS (Render met SESSION_COOKIE_SECURE=1)
        if app.config.get("SESSION_COOKIE_SECURE"):
            response.headers.setdefault("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload")
        return response


def _register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(_e):
        return render_template(
            "error.html", code=404, message="Cette page n'existe pas."
        ), 404

    @app.errorhandler(429)
    def rate_limited(_e):
        return render_template(
            "error.html", code=429, message="Trop de requêtes — réessaie dans une minute."
        ), 429

    @app.errorhandler(CSRFError)
    def csrf_error(_e):
        return render_template(
            "error.html", code=400, message="Session expirée : recharge la page et réessaie."
        ), 400


def _register_cli(app):
    @app.cli.command("set-plan")
    @click.argument("email")
    @click.argument("plan", type=click.Choice(["free", "pro"]))
    def set_plan(email, plan):
        """Change le plan d'un client : flask --app wsgi set-plan EMAIL pro"""
        from .models import User

        user = User.query.filter_by(email=email.strip().lower()).first()
        if user is None:
            raise click.ClickException(f"Aucun utilisateur avec l'email {email}")
        user.plan = plan
        db.session.commit()
        click.echo(f"{user.email} -> plan {plan}")
