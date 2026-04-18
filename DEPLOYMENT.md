# Railway Deployment Guide

This Reflex app is configured for deployment on Railway using Docker.

## Quick Start

### 1. Connect Your Repository to Railway

1. Go to [railway.app](https://railway.app)
2. Create a new project
3. Click "Deploy from GitHub" and authorize Railway
4. Select this repository
5. Railway will automatically detect the Dockerfile and deploy

### 2. Configure Environment Variables (if needed)

In Railway's dashboard under your project:
- Go to Variables
- Add any required environment variables for your Reflex app
- Common variables:
  - `REFLEX_ENV=prod` (usually handled automatically)
  - Any API keys or secrets your app needs

### 3. Monitor Deployment

- Railway will automatically build and deploy from the Dockerfile
- Check the Deployment tab in Railway to see logs
- Your app will be assigned a public URL automatically

## How It Works

- **Dockerfile**: Builds a minimal Python 3.11 image with your dependencies
  - Installs dependencies using `uv` (fast, lockfile-based)
  - Pre-builds the Reflex frontend during image build
  - Runs Reflex in production mode on port 3000

- **railway.toml**: Configures Railway-specific settings
  - Specifies Docker as the build method
  - Sets the start command
  - Configures restart policy

## Troubleshooting

### Port Issues
Railway automatically sets the `PORT` environment variable. The Dockerfile exposes port 3000 and the app listens on `$PORT`.

### Build Failures
Check Railway logs for details. Common issues:
- Missing dependencies: Update `pyproject.toml`
- Python version mismatch: Ensure Python 3.11+
- Memory limits: Railway free tier has limited memory; may need to upgrade for large builds

### Out of Memory (OOM) Errors
Railway free tier has ~512MB RAM, which may be insufficient for building Reflex apps.

**Solutions:**
1. **Upgrade Railway plan** — Switch to a paid plan with 1GB+ RAM (recommended)
2. **Use a lighter image** — The Dockerfile uses Python 3.11-slim and defers builds to runtime
3. **Monitor usage** — Check Railway dashboard → Metrics to see actual memory usage

The app should stabilize once deployed, as the initial build uses the most memory.

### App Not Starting
- Check Railway logs for startup errors
- Ensure environment variables are set if required
- Verify Reflex build completes successfully (first startup may take 1-2 minutes)

## Local Testing

To test the Docker build locally:

```bash
docker build -t reflex-app .
docker run -p 3000:3000 reflex-app
```

Then visit `http://localhost:3000`
