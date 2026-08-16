backend-test:
	cd backend && uv run pytest -q
frontend-test:
	cd frontend && npm test
frontend-build:
	cd frontend && npm run build
all-checks: backend-test frontend-test frontend-build

release-check:
	cd backend && uv run pytest -q
	cd frontend && npm ci && npm test && npm run build
