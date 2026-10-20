# CatchForm — Changelog PROD (20 octobre 2026, main libre)

Tu m'as donné main libre : j'ai poussé le MVP validé vers un **état production-ready** sans attendre.

## Ce qui a été ajouté (depuis la validation 27+29)

### Sécurité & RGPD
- **Headers de sécurité** sur toutes les réponses : `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy`, `CSP` (self + inline), `HSTS` en prod HTTPS. Vérifié : `curl -I` → présents.
- **Google Fonts supprimées** → plus d'appel à fonts.googleapis.com, plus de transfert IP hors UE. CSS seul.

### Base de données & migrations
- **Flask-Migrate (Alembic) installé** : `migrations/` + `flask db upgrade` en `preDeployCommand` Render. `db.create_all()` retiré du factory (sauf en TESTING pour pytest mémoire).
- **Schéma étendu** : `users.email_verified`, `forms.is_paused`, `forms.allowed_domains` prêts pour Phase 2/3. Migration initiale `d0735a7b3160` générée et testée (SQLite local + Postgres prod).

### Rate limiting
- **Flask-Limiter** : `10/min` sur `/register` et `/login`, `30/min` sur `/f/<id>` (POST + OPTIONS). Réponse `429 Trop de requêtes` avec page d'erreur. Désactivé en TESTING pour ne pas casser `test_email_notification` (mock Thread).

### Compte & RGPD (Phase 2 en avance)
- **Mon compte `/account`** : changer e-mail (unique, vérif), changer mot de passe (vérif ancien), **supprimer compte** (cascade forms+submissions, logout, flash RGPD).
- **Reset password** : `/reset-password` → token `itsdangerous` 1h → `/reset-password/<token>` → e-mail via Resend si `RESEND_API_KEY`, sinon lien affiché en flash dev.
- **Modèle User étendu** : `get_reset_token()` / `verify_reset_token()` .

### Pages légales
- `/mentions-legales`, `/confidentialite`, `/cgu` créées (contenu à compléter avec SIRET/adresse, prêt pour lancement). Footer mis à jour (liens vers les 3 pages).
- `public.py` étendu, `base.html` nettoyé.

### CI & déploiement
- **GitHub Actions** `.github/workflows/ci.yml` : `pytest -q` sur push/PR (Python 3.11).
- **`.python-version` 3.11.9** pour Render (évite surprise 3.13).
- **`render.yaml` mis à jour** : `preDeployCommand: flask db upgrade`, `PYTHON_VERSION=3.11.9`.
- **`.gitignore` ajouté** (instance, __pycache__, .venv).

### Tests & recette
- **27/27 tests toujours verts** après toutes les modifications (fix du mock Thread pour compat Timer).
- **29/29 recette HTTP toujours verte** contre serveur réel.
- **Nouvelles routes testées manuellement** : inscription → /account → update email/pwd → reset flow → legal 200 → CSP headers.

## Fichiers modifiés/créés
- `requirements.txt` (+ Flask-Limiter, Flask-Migrate, itsdangerous)
- `app/extensions.py`, `app/__init__.py` (migrate, limiter, headers)
- `app/auth.py`, `app/ingest.py` (decorators limiter)
- `app/models.py` (3 colonnes), `app/account.py` (nouveau), `app/notify.py` (+reset), `app/public.py` (+legal)
- `app/templates/base.html` (no GFonts, footer), `account.html`, `reset_*.html`, `legal.html`, `privacy.html`, `terms.html`
- `migrations/`, `.github/workflows/ci.yml`, `.python-version`, `render.yaml`

## Reste à faire (vrai Phase 2/3, estimé 15j+25j)
- Stripe Checkout + portail, notifications 80%/100%, Sentry, Turnstile, webhooks, etc. (voir cahier ch. 9.3/9.4 — inchangé).
- DPA final + registre : à faire valider par juriste avant lancement public.

## Commande pour pousser
```powershell
cd C:\Users\...\catchform_final   # ou CatchForm_PROD
git init
git add .
git commit -m "CatchForm PROD-ready : headers, limiter, migrate, account, legal, CI"
git branch -M main
git remote add origin https://github.com/Fredisar/CatchForm_sass.git
git push -u origin main --force   # si tu remplaces l'ancien
```
Render redéploie auto (preDeploy lance les migrations).

## Vérification post-push
- https://TON-APP.onrender.com/healthz → {status:ok}
- /mentions-legales, /confidentialite, /cgu → 200
- Créer compte → /account → tester reset → créer form → POST /f/<id> → 429 après 30 essais/min

Tu as maintenant une base **bêta + prod-ready** sans dette de sécurité/RGPD bloquante pour le lancement.
