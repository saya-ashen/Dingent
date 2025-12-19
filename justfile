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
# [已删除] DB_DIR 变量

install:
    @echo "Installing all monorepo dependencies..."
    @bun install --frozen-lockfile

# =====================
# 1. 构建 Frontend (Standalone 模式)
# =====================
# [已删除] build-dashboard 任务
build-frontend:
    @echo "Building Frontend (Standalone)..."
    # 确保 next.config.ts 中已开启 output: "standalone"
    @(cd ui/ && bun install && bun run build --filter=frontend)

# =====================
# 2. 组装 (Assemble) - 现已简化为单一应用提取
# =====================
assemble:
    @echo "Starting assembly of frontend application..."
    @rm -rf {{DEPLOY_DIR}}
    @mkdir -p {{DEPLOY_DIR}}/node_modules
    @mkdir -p {{DEPLOY_DIR}}/apps/frontend

    # [1/3] 复制 node_modules
    # 直接使用 frontend 产生的 standalone node_modules，无需合并
    @echo "Copying node_modules..."
    @cp -r {{FE_DIR}}/.next/standalone/node_modules/* {{DEPLOY_DIR}}/node_modules/

    # [2/3] 复制应用服务端代码 (Server Logic)
    @echo "Copying application server code..."
    # Next.js standalone 在 monorepo 下通常会保留目录结构，如 .next/standalone/apps/frontend
    @cp -r {{FE_DIR}}/.next/standalone/apps/frontend/* {{DEPLOY_DIR}}/apps/frontend/
    @cp {{FE_DIR}}/.next/standalone/apps/frontend/server.js {{DEPLOY_DIR}}/apps/frontend/ || echo "Warning: server.js not found, check standalone output structure."

    # [3/3] 复制静态资源 (Static Assets & Public)
    # Standalone 不包含 .next/static 和 public，必须手动复制
    @echo "Injecting static assets..."

    @mkdir -p {{DEPLOY_DIR}}/apps/frontend/.next/static
    @cp -r {{FE_DIR}}/.next/static/* {{DEPLOY_DIR}}/apps/frontend/.next/static/
    @cp -r {{FE_DIR}}/public {{DEPLOY_DIR}}/apps/frontend/

    # [可选] 复制根目录 package.json (如果 server.js 运行需要读取项目元数据)
    @cp package.json {{DEPLOY_DIR}}/ || true

    @echo "✅ Assembly complete. Structure created at {{DEPLOY_DIR}}"

# =====================
# 3. 裁剪 (Prune) - 保持不变，用于减小体积
# =====================
prune:
    @echo "[prune] Pruning node_modules in {{DEPLOY_DIR}}..."
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
# 4. 打包 (Package)
# =====================
package:
    @echo "Compressing artifacts to 'build/static.tar.gz'..."
    # 确保 build 目录存在
    @mkdir -p build
    @tar -czf build/static.tar.gz -C {{DEPLOY_DIR}} .
    @ls -lh build/static.tar.gz
    @echo "🚀 Ready for deployment!"

# =====================
# 总入口：构建 UI
# =====================
build-ui: build-frontend assemble prune package
    @echo "🎉 Frontend application built, prepared, and packaged."
