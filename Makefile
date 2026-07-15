.PHONY: install test test-py test-fe dev build lint lint-py lint-fe clean

# 安装所有依赖
install:
	pip install -e .
	cd frontend && npm install

# 跑全部测试
test: test-py test-fe

test-py:
	python -m pytest tests/

test-fe:
	cd frontend && npm test

# 开发模式（热更新）
dev:
	@echo "终端1: ma --web"
	@echo "终端2: cd frontend && npm run dev"

# 前端构建
build:
	cd frontend && npm run build

# 代码检查
lint: lint-py lint-fe

lint-py:
	ruff check src/ tests/

lint-fe:
	cd frontend && npx tsc -b --noEmit

# 清理构建产物
clean:
	rm -rf src/kernel/web/static/
	rm -rf frontend/node_modules/.vite/