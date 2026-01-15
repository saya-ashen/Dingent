# Deployment Guide

This guide explains how to deploy Dingent with different configurations.

## Subpath Deployment

If you need to deploy Dingent under a subpath (e.g., `/dingent/web`), you can use the `--base-path` option.

### Using the CLI

To run Dingent under a subpath, use the `--base-path` flag:

```bash
dingent run --base-path /dingent/web
```

This will:
- Configure the frontend to serve all assets and pages under `/dingent/web`
- Configure the backend API to be accessible at `/dingent/web/api/v1`
- Update all internal redirects and links to respect the base path

### Example: Deploying Behind a Reverse Proxy

If you're deploying behind a reverse proxy (like Nginx) that strips the prefix:

#### Nginx Configuration

```nginx
location /dingent/web/ {
    # Frontend (Next.js)
    proxy_pass http://localhost:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /dingent/web/api/v1/ {
    # Backend (FastAPI)
    proxy_pass http://localhost:8000/api/v1/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Then run:
```bash
dingent run --base-path /dingent/web
```

### Environment Variables

Alternatively, you can set environment variables directly:

#### For Frontend:
```bash
export NEXT_PUBLIC_BASE_PATH=/dingent/web
```

#### For Backend:
```bash
export API_ROOT_PATH=/dingent/web
```

Then run the services separately:

```bash
# Backend
cd src
uvicorn dingent.server.main:app --host 0.0.0.0 --port 8000

# Frontend
cd ui
npm run build
npm start
```

## Docker Deployment

When using Docker, you can pass the base path as an environment variable:

```dockerfile
# Example docker-compose.yml
version: '3.8'
services:
  backend:
    image: dingent-backend
    environment:
      - API_ROOT_PATH=/dingent/web
    ports:
      - "8000:8000"
  
  frontend:
    image: dingent-frontend
    environment:
      - NEXT_PUBLIC_BASE_PATH=/dingent/web
      - BACKEND_URL=http://backend:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend
```

## Verification

After starting with a base path, verify the configuration:

1. **Frontend Access**: Visit `http://localhost:3000/dingent/web` (or your configured domain)
2. **API Access**: Check `http://localhost:8000/dingent/web/api/v1/health`
3. **Authentication**: Ensure login redirects work correctly
4. **Assets**: Verify that all CSS, JS, and images load correctly

## Troubleshooting

### Issue: 404 errors for assets
- Ensure `NEXT_PUBLIC_BASE_PATH` is set correctly for the frontend
- Check that your reverse proxy is configured to pass through the base path

### Issue: API calls failing
- Verify `API_ROOT_PATH` is set for the backend
- Check that the frontend's `BACKEND_URL` points to the correct backend URL
- Ensure your reverse proxy forwards API requests correctly

### Issue: Login redirects to wrong path
- The middleware should automatically handle base paths
- Verify that `NEXT_PUBLIC_BASE_PATH` is set before building the frontend

## Notes

- The base path must start with a forward slash (e.g., `/dingent/web`)
- The base path should NOT end with a trailing slash
- When building the frontend for production, ensure `NEXT_PUBLIC_BASE_PATH` is set during build time
- The backend's `API_ROOT_PATH` can be set at runtime
