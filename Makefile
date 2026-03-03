.PHONY: test-backend test-frontend test-all test-backend-cov test-frontend-cov test-cov-all

test-backend:
	@echo "Running Python Backend Tests..."
	cd backend && source venv/bin/activate && pytest -v

test-frontend:
	@echo "Running React Frontend Tests..."
	cd frontend && npm run test

test-all: test-backend test-frontend
	@echo "All tests passed successfully! 🚀"

test-backend-cov:
	@echo "Running Python Backend Tests with Coverage..."
	cd backend && source venv/bin/activate && pytest --cov=. --cov-report=term-missing --cov-fail-under=85 tests/ -v

test-frontend-cov:
	@echo "Running React Frontend Tests with Coverage..."
	cd frontend && npm run test:coverage

test-cov-all: test-backend-cov test-frontend-cov
	@echo "All coverage checks passed successfully! 🚀"