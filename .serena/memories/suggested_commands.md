# Suggested Commands for Development

## Testing Commands
```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_<component>.py -v

# Run with coverage
pytest --cov=app --cov-report=term-missing

# Run specific test method
pytest tests/unit/test_<component>.py::<TestClass>::<test_method> -v

# Run integration tests
pytest tests/integration/ -v
```

## Development Commands
```bash
# Install dependencies
uv pip install -r requirements.txt

# Run FastAPI app locally
uvicorn app.main:app --reload --port 8000

# Run with environment variables
python -m uvicorn app.main:app --reload --env-file .env

# Generate requirements
uv pip compile pyproject.toml -o requirements.txt
```

## Docker Commands
```bash
# Run services locally
docker-compose up -d

# View logs
docker-compose logs -f <service>

# Stop services
docker-compose down
```

## Kubernetes Commands
```bash
# Apply configurations
kubectl apply -f kubernetes/<file>.yaml

# Deploy observability stack
cd kubernetes/observability/charts
./deploy.sh

# Check pod status
kubectl get pods -n <namespace>

# View logs
kubectl logs -n <namespace> <pod-name>
```

## Git Commands
```bash
# Current branch
git branch --show-current

# Status
git status

# Create feature branch
git checkout -b feature/<feature-name>

# Commit with conventional format
git commit -m "<type>(<scope>): <description>"
```

## Code Analysis
```bash
# Generate codebase summary
repomix

# Check code coverage
pytest --cov=app --cov-report=html
open htmlcov/index.html
```