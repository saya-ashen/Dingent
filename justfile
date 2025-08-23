# build-admin: Builds the admin dashboard and copies assets.
build-admin:
    @echo "Building admin dashboard..."
    @(cd ui/admin-dashboard && bun install && bun run build)

    @echo "Copying admin dashboard artifacts..."
    @rm -rf src/dingent/static/admin_dashboard
    @mkdir -p src/dingent/static/admin_dashboard
    @cp -r ui/admin-dashboard/dist/. src/dingent/static/admin_dashboard/

    @echo "✅ Admin dashboard built and copied successfully."


# build-frontend: Builds the Next.js frontend for standalone deployment.
build-frontend:
    @echo "Building user frontend..."
    # Step 1: Navigate to the frontend directory and run the build.
    @(cd ui/frontend && bun install && bun run build)

    @echo "Copying Next.js standalone artifacts to 'src/dingent/static/frontend'..."
    # Step 2: Clean and recreate the destination directory for a fresh copy.
    @rm -rf src/dingent/static/frontend
    @mkdir -p src/dingent/static/frontend

    # Step 3: Copy the core standalone server files (like server.js, node_modules).
    @cp -r ui/frontend/.next/standalone/. src/dingent/static/frontend/

    # Step 4: The standalone server needs the '.next/static' and 'public' folders
    # to serve assets correctly. We copy them to the expected locations.
    @cp -r ui/frontend/.next/static src/dingent/static/frontend/.next/
    @cp -r ui/frontend/public src/dingent/static/frontend/

    @echo "✅ User frontend built and copied successfully."


# build-ui: A helper command to build both frontend applications.
build-ui: build-admin build-frontend
    @echo "🚀 All UI applications have been built."
