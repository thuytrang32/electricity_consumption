# Continuous Deployment guide

## Current pipeline boundary

The main workflow performs:

```text
lint → test → build → publish Docker images to GHCR
```

The separate `deploy.yml` performs deployment to a Docker host, but is initially triggered manually so you can configure and verify the target safely.

## Option A 

Demonstrate locally:

```bash
docker compose up --build
```

## Option B — configure a real Docker deployment host

You can use a VPS, cloud VM or company VM. The host needs:

- Linux
- Docker
- Docker Compose plugin
- SSH access

One-time host setup:

```bash
sudo mkdir -p /opt/electricity-predictor
sudo chown "$USER":"$USER" /opt/electricity-predictor
cd /opt/electricity-predictor
```

Copy `docker-compose.prod.yml` there and create `.env`:

```env
POSTGRES_DB=electricity
POSTGRES_USER=appuser
POSTGRES_PASSWORD=use-a-strong-password
```

If your GHCR images are private, log the server into GHCR using a GitHub token with package read permission.

## GitHub Actions secrets

Repository → Settings → Secrets and variables → Actions:

```text
DEPLOY_HOST      server hostname/IP
DEPLOY_USER      SSH username
DEPLOY_SSH_KEY   private SSH key
```

## Manual deployment first

1. Push to `main`.
2. Wait for `CI + Continuous Delivery` to finish successfully.
3. Open Actions → `Deploy to Docker host`.
4. Run it with `latest` or a commit SHA.

The workflow SSHs to the host and runs conceptually:

```bash
export BACKEND_IMAGE=ghcr.io/<owner>/electricity-backend:<tag>
export FRONTEND_IMAGE=ghcr.io/<owner>/electricity-frontend:<tag>
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
curl --fail http://localhost/health
```

## Turn it into automatic Continuous Deployment

Only after manual deployment works, change the deployment workflow to trigger automatically after the delivery workflow succeeds, or on pushes to `main`.

Conceptually:

```text
git push main
  ↓
lint
  ↓
test
  ↓
build
  ↓
publish images
  ↓
deploy host
  ↓
health/smoke check
```

PostgreSQL data is stored in a named Docker volume, so recreating the application containers does not delete prediction history.
