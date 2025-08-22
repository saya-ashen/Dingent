build-admin:
    @echo "Building admin dashboard..."
    # Step 1: Navigate to the frontend directory and run the build command.
    # The command is run in a subshell `()` so the change of directory doesn't
    # affect subsequent commands.
    @(cd ui/admin-dashboard && bun run build)

    @echo "Copying build artifacts..."
    # Step 2: Ensure the destination directory is clean by removing it first.
    @rm -rf src/dingent/static/admin_dashboard
    # Recreate the destination directory. The `-p` flag creates parent directories
    # if they don't exist and doesn't error if the directory already exists.
    @mkdir -p src/dingent/static/admin_dashboard

    # Step 3: Copy all files from the build output directory to the destination.
    # The `.` at the end of the source path ensures that the *contents* of 'dist' are copied.
    @cp -r ui/admin-dashboard/dist/. src/dingent/static/admin_dashboard/

    @echo "✅ Admin dashboard built and copied successfully."
