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

# =====================
# 内部：裁剪函数配方（可单独运行： just prune-next）
# =====================
prune-next:
	@echo "[prune] Start pruning Next.js standalone..."
	@if [ ! -d ui/frontend/.next/standalone/node_modules/next/dist/compiled ]; then \
	  echo "[prune] compiled directory not found, maybe build failed or not standalone build"; \
	  exit 0; \
	fi
	# 1. 裁剪 swc 平台二进制
	@echo "[prune] Keep swc platform pattern: $${SWC_PLATFORM}"
	@cd ui/frontend/.next/standalone/node_modules/next/dist/compiled; \
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
	  rm -rf ui/frontend/.next/standalone/node_modules/@img || true; \
	fi
	@echo "[prune] Size after prune:"
	@du -sh ui/frontend/.next/standalone || true
	@echo "[prune] Done."

# =====================
# 构建 Admin
# =====================
build-admin:
	@echo "Building admin dashboard..."
	@(cd ui/admin-dashboard && bun install && bun run build)

	@echo "Copying admin dashboard artifacts..."
	@rm -rf src/dingent/static/admin_dashboard
	@mkdir -p src/dingent/static/admin_dashboard
	@cp -r ui/admin-dashboard/dist/. src/dingent/static/admin_dashboard/

	@echo "✅ Admin dashboard built and copied successfully."

# =====================
# 构建 Frontend (Next.js) + 裁剪
# =====================
build-frontend:
	@echo "Building user frontend (Next.js standalone)..."
	@(cd ui/frontend && bun install && bun run build)

	@echo "Pruning standalone output..."
	@just prune-next

	@echo "Copying pruned Next.js standalone artifacts to 'src/dingent/static/frontend'..."
	@rm -rf src/dingent/static/frontend
	@mkdir -p src/dingent/static/frontend
	@cp -r ui/frontend/.next/standalone/. src/dingent/static/frontend/

	@echo "Copying .next/static (client assets)..."
	@cp -r ui/frontend/.next/static src/dingent/static/frontend/.next/

	@echo "Copying public/ assets..."
	@cp -r ui/frontend/public src/dingent/static/frontend/ 2>/dev/null || true

	@echo "Final size (human readable):"
	@du -sh src/dingent/static/frontend || true
	@echo "✅ User frontend built, pruned and copied successfully."

# =====================
# 同时构建两个
# =====================
build-ui: build-admin build-frontend
	@echo "🚀 All UI applications have been built."
