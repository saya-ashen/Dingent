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
FE_DIR := "ui/apps/frontend"
DB_DIR := "ui/apps/dashboard"

install:
    @echo "Installing all monorepo dependencies..."
    @bun install --frozen-lockfile

# =====================
# 1. 构建 Dashboard (改为 Standalone 模式)
# =====================
build-dashboard:
    @echo "Building Dashboard (Standalone)..."
    # 确保 next.config.ts 中已开启 output: "standalone" 且移除了 output: "export"
    @(cd ui/ && bun install && bun run build --filter=dashboard)

# =====================
# 2. 构建 Frontend (Standalone 模式)
# =====================
build-frontend:
    @echo "Building Frontend (Standalone)..."
    @(cd ui/ && bun install && bun run build --filter=frontend)

# =====================
# 3. 核心：组装与合并 (Merge & Assemble)
# =====================
assemble:
    @echo "Starting assembly of merged standalone applications..."
    @rm -rf {{DEPLOY_DIR}}
    @mkdir -p {{DEPLOY_DIR}}/node_modules
    @mkdir -p {{DEPLOY_DIR}}/apps

    # [1/4] 合并 node_modules (先拷 frontend，再拷 dashboard 覆盖，利用 Common Dependencies)
    @echo "Merging node_modules..."
    @cp -r {{FE_DIR}}/.next/standalone/node_modules/* {{DEPLOY_DIR}}/node_modules/
    @cp -r {{DB_DIR}}/.next/standalone/node_modules/* {{DEPLOY_DIR}}/node_modules/

    # [2/4] 复制应用服务端代码 (Server Logic)
    # 注意：Standalone 通常会保留 ui/apps/xxx 的完整目录结构，我们需要将其扁平化到 apps/ 下
    @echo "Copying application server code..."
    @mkdir -p {{DEPLOY_DIR}}/apps/frontend
    @mkdir -p {{DEPLOY_DIR}}/apps/dashboard

    # 复制 Frontend 代码 (根据实际生成的层级调整，通常在 standalone/ui/apps/frontend)
    @cp -r {{FE_DIR}}/.next/standalone/apps/frontend/* {{DEPLOY_DIR}}/apps/frontend/
    @cp {{FE_DIR}}/.next/standalone/apps/frontend/server.js {{DEPLOY_DIR}}/apps/frontend/ || echo "Warning: server.js not found in expected path, check standalone output structure."

    # 复制 Dashboard 代码
    @cp -r {{DB_DIR}}/.next/standalone/apps/dashboard/* {{DEPLOY_DIR}}/apps/dashboard/
    @cp {{DB_DIR}}/.next/standalone/apps/dashboard/server.js {{DEPLOY_DIR}}/apps/dashboard/ || echo "Warning: server.js not found."

    # [3/4] 复制静态资源 (Static Assets & Public)
    # Standalone 不包含 .next/static 和 public，必须手动复制
    @echo "Injecting static assets..."

    # Frontend 资源
    @mkdir -p {{DEPLOY_DIR}}/apps/frontend/.next/static
    @cp -r {{FE_DIR}}/.next/static/* {{DEPLOY_DIR}}/apps/frontend/.next/static/
    @cp -r {{FE_DIR}}/public {{DEPLOY_DIR}}/apps/frontend/

    # Dashboard 资源
    @mkdir -p {{DEPLOY_DIR}}/apps/dashboard/.next/static
    @cp -r {{DB_DIR}}/.next/static/* {{DEPLOY_DIR}}/apps/dashboard/.next/static/
    @cp -r {{DB_DIR}}/public {{DEPLOY_DIR}}/apps/dashboard/

    # [4/4] 复制根目录必要文件
    @cp package.json {{DEPLOY_DIR}}/ || true

    @echo "✅ Assembly complete. Structure created at {{DEPLOY_DIR}}"

# =====================
# 4. 裁剪 (Prune) - 针对合并后的 node_modules
# =====================
prune:
    @echo "[prune] Pruning merged node_modules in {{DEPLOY_DIR}}..."
    @if [ ! -d {{DEPLOY_DIR}}/node_modules/next/dist/compiled ]; then \
        echo "[prune] Target directory not found. Run 'just assemble' first."; exit 1; \
    fi

    # 1. 裁剪 swc 平台二进制
    @echo "[prune] Keeping swc platform: $${SWC_PLATFORM}"
    @cd {{DEPLOY_DIR}}/node_modules/next/dist/compiled; \
    for d in @next/swc-*; do \
        if echo "$d" | grep -q "$$SWC_PLATFORM"; then \
            if [ "$VERBOSE" = "1" ]; then echo "  keep $$d"; fi; \
        else \
            echo "  remove $$d"; rm -rf "$$d"; \
        fi; \
    done

    # 2. 删除 @img (可选)
    @if [ "$STRIP_IMG" = "1" ]; then \
        echo "[prune] Removing @img"; \
        rm -rf {{DEPLOY_DIR}}/node_modules/@img || true; \
    fi

    # 3. 删除 sourcemaps (可选)
    @if [ "$STRIP_SOURCE_MAPS" = "1" ]; then \
        echo "[prune] Removing source maps (*.map)"; \
        find {{DEPLOY_DIR}} -name "*.map" -type f -delete || true; \
    fi

    @echo "[prune] Final size of deploy folder:"
    @du -sh {{DEPLOY_DIR}}

# =====================
# 5. 打包 (Package)
# =====================
package:
    @echo "Compressing artifacts to 'build/static.tar.gz'..."
    @tar -czf build/static.tar.gz -C {{DEPLOY_DIR}} .
    @ls -lh build/static.tar.gz
    @echo "🚀 Ready for deployment!"

# =====================
# 总入口：构建 UI (Build -> Assemble -> Prune -> Package)
# =====================
build-ui: build-dashboard build-frontend assemble prune package
    @echo "🎉 All UI applications built, merged, and packaged."
