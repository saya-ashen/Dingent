# 让所有定义的变量导出到配方的环境中
set export
# 更安全的 shell 行为
set shell := ["bash", "-eu", "-o", "pipefail", "-c"]

# =====================
# 可覆盖变量（命令行： just SWC_PLATFORM=linux-x64-musl build-frontend）
# =====================
SWC_PLATFORM      := "linux-x64-gnu"   # 例如 linux-x64-musl / darwin-arm64 / darwin-x64
STRIP_IMG         := "1"               # 1=删除 next/dist/compiled/@img
STRIP_SOURCE_MAPS := "1"               # 1=删除 *.map
STRIP_TESTS       := "1"               # 1=删除 tests/examples/docs 等目录
STRIP_READMES     := "0"               # 1=删除 README/CHANGELOG（小空间，默认保留）
STRIP_LICENSES    := "0"               # 1=删除 LICENSE*（注意合规风险）
VERBOSE           := "0"               # 1=更多输出

install:
    @echo "Installing all monorepo dependencies from the root..."
    @bun install

# =====================
# 内部：裁剪函数配方（可单独运行： just prune-next）
# =====================
prune-next:
	@echo "[prune] Start pruning Next.js standalone..."
	@if [ ! -d ui/apps/frontend/.next/standalone/apps/frontend/node_modules/next/dist/compiled ]; then \
	  echo "[prune] compiled directory not found, maybe build failed or not standalone build"; \
	  exit 0; \
	fi
	# 1. 裁剪 swc 平台二进制
	@echo "[prune] Keep swc platform pattern: $${SWC_PLATFORM}"
	@cd ui/apps/frontend/.next/standalone/apps/frontend/node_modules/next/dist/compiled; \
	for d in @next/swc-*; do \
	  if echo "$d" | grep -q "$$SWC_PLATFORM"; then \
	    if [ "$VERBOSE" = "1" ]; then echo "  keep $$d"; fi; \
	  else \
	    echo "  remove $$d"; rm -rf "$$d"; \
	  fi; \
	done
	#  删除 @img
	@if [ "$STRIP_IMG" = "1" ]; then \
	  echo "[prune] Removing @img (image optimizer binaries)"; \
	  rm -rf ui/apps/frontend/.next/standalone/node_modules/@img || true; \
	fi
	@echo "[prune] Size after prune:"
	@du -sh ui/apps/frontend/.next/standalone || true
	@echo "[prune] Done."

# =====================
# 构建 dashboard
# =====================
build-dashboard:
	@echo "Building dashboard..."
	@(cd ui/ && bun install && bun run build --filter=dashboard)

	# @echo "Copying dashboard artifacts..."
	# @rm -rf src/dingent/static/dashboard
	# @mkdir -p src/dingent/static/dashboard
	# @cp -r ui/apps/dashboard/out/. src/dingent/static/dashboard/

	@echo "Copying dashboard into frontend/public..."
	@mkdir -p ui/apps/frontend/public/dashboard
	@rm -rf ui/apps/frontend/public/dashboard/*
	@cp -r ui/apps/dashboard/out/. ui/apps/frontend/public/dashboard/

	@echo "Done"


# =====================
# 构建 Frontend (Next.js) + 裁剪
# =====================
build-frontend:
	@echo "Building user frontend (Next.js standalone)..."
	@(cd ui/ && bun install && bun run build --filter=frontend)

	@echo "Pruning standalone output..."
	@just prune-next

	@echo "Copying pruned Next.js standalone artifacts to 'src/dingent/static'..."
	@rm -rf src/dingent/static
	@mkdir -p src/dingent/static
	@cp -r ui/apps/frontend/.next/standalone/. src/dingent/static

	@echo "Copying .next/static (client assets)..."
	@cp -r ui/apps/frontend/.next/static src/dingent/static/apps/frontend/.next/

	@echo "Copying public/ assets..."
	@cp -r ui/apps/frontend/public src/dingent/static/apps/frontend/ 2>/dev/null || true

	@echo "Final size (human readable):"
	@du -sh src/dingent/static || true
	@echo "✅ User frontend built, pruned and copied successfully."

# =====================
# 同时构建两个
# =====================
build-ui: build-dashboard build-frontend
	@echo "🚀 All UI applications have been built."
