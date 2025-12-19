# 让所有定义的变量导出到配方的环境中
set export
# 更安全的 shell 行为
set shell := ["sh","-c"]
set windows-shell := ["sh", "-c"]

# =====================
# 变量定义
# =====================
SWC_PLATFORM := if os() == "windows" { "win32-x64-msvc" } else { "linux-x64-gnu" }
STRIP_IMG         := "1"
STRIP_SOURCE_MAPS := "1"
STRIP_TESTS       := "1"
VERBOSE           := "0"

# 定义构建和输出路径
DEPLOY_DIR := "build/deploy"
FE_DIR := "ui"

install:
    @echo "Installing all monorepo dependencies..."
    @bun install --frozen-lockfile

build:
    @echo "Building Frontend (Standalone)..."
    @(cd ui/ && bun install && bun run build)

assemble:
    @echo "Starting assembly of frontend application..."
    @rm -rf {{DEPLOY_DIR}}
    @mkdir -p {{DEPLOY_DIR}}/frontend


    @echo "Copying application server code..."
    @cp -r {{FE_DIR}}/.next/standalone/. {{DEPLOY_DIR}}/frontend/

    @echo "Injecting static assets..."

    @mkdir -p {{DEPLOY_DIR}}/frontend/.next/static
    @cp -r {{FE_DIR}}/.next/static/* {{DEPLOY_DIR}}/frontend/.next/static/
    @cp -r {{FE_DIR}}/src/public {{DEPLOY_DIR}}/frontend/

    @echo "✅ Assembly complete. Structure created at {{DEPLOY_DIR}}"

prune:
    @echo "[prune] Pruning node_modules in {{DEPLOY_DIR}}..."
    @if [ ! -d {{DEPLOY_DIR}}/frontend/node_modules/next/dist/compiled ]; then \
        echo "[prune] Target directory not found. Run 'just assemble' first."; exit 1; \
    fi

    @echo "[prune] Keeping swc platform: $${SWC_PLATFORM}"
    @cd {{DEPLOY_DIR}}/frontend/node_modules/next/dist/compiled; \
    for d in @next/swc-*; do \
        if echo "$d" | grep -q "$$SWC_PLATFORM"; then \
            if [ "$VERBOSE" = "1" ]; then echo "  keep $$d"; fi; \
        else \
            echo "  remove $$d"; rm -rf "$$d"; \
        fi; \
    done

    @if [ "$STRIP_IMG" = "1" ]; then \
        echo "[prune] Removing @img"; \
        rm -rf {{DEPLOY_DIR}}/frontend/node_modules/@img || true; \
    fi

    @if [ "$STRIP_SOURCE_MAPS" = "1" ]; then \
        echo "[prune] Removing source maps (*.map)"; \
        find {{DEPLOY_DIR}} -name "*.map" -type f -delete || true; \
    fi

    @echo "[prune] Final size of deploy folder:"
    @du -sh {{DEPLOY_DIR}}

package:
    @echo "Compressing artifacts to 'build/static.tar.gz'..."
    @mkdir -p build
    @tar -czf build/static.tar.gz -C {{DEPLOY_DIR}} .
    @ls -lh build/static.tar.gz
    @echo "🚀 Ready for deployment!"

build-ui: build assemble prune package
    @echo "🎉 Frontend application built, prepared, and packaged."

build-exe:
  pyinstaller dingent.spec
