# Contributing to Trade Bot

<!-- AUTO-GENERATED -->

This document provides guidelines for development setup, testing, code style, and the contribution process.

**Last Updated:** 2024-04-03

## Development Setup

### 1. Clone and Install

```bash
git clone <repo-url>
cd Trade-Bot
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Set Up Environment Variables

```bash
cp .env.example .env
# Edit .env with your credentials (optional for paper mode)
```

### 3. Verify Installation

```bash
trade-bot --help
pytest --version
ruff --version
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Tests with Coverage

```bash
pytest --cov=src --cov-report=term-missing
```

This produces a coverage report showing which lines are not covered by tests. **Minimum 80% coverage required** for new code.

### Run Tests by Category

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Specific test file
pytest tests/test_grid_engine.py -v

# Specific test function
pytest tests/test_grid_engine.py::test_grid_levels -v
```

### Watch Mode

If you have pytest-watch installed:
```bash
ptw
```

This reruns tests whenever files change.

## Code Style

### Formatting

Trade Bot uses **ruff** for linting and formatting. All code must pass ruff checks before merging.

```bash
# Format code
ruff format src/ tests/

# Check for issues
ruff check src/ tests/

# Fix issues automatically
ruff check --fix src/ tests/
```

### Ruff Configuration

Configuration is in `pyproject.toml`:

```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = [
    "E", "W",  # pycodestyle
    "F",       # pyflakes
    "I",       # isort (import sorting)
    "B",       # flake8-bugbear (common bugs)
    "UP",      # pyupgrade (modern Python)
    "S",       # bandit (security)
    "RUF",     # ruff-specific
]
```

### Code Style Conventions

- **Line Length:** 100 characters (enforced by ruff)
- **Imports:** Sorted automatically by ruff (isort)
- **Naming:**
  - `PascalCase` for classes and dataclasses
  - `snake_case` for functions and variables
  - `UPPER_SNAKE_CASE` for constants
- **Type Hints:** All function signatures must include type hints
  ```python
  def calculate_profit(entry: float, exit: float, amount: float) -> float:
      return (exit - entry) * amount
  ```
- **Docstrings:** Google-style docstrings for classes and public functions
  ```python
  def calculate_grid_levels(lower: float, upper: float, num_grids: int) -> list[float]:
      """Calculate evenly-spaced price levels between lower and upper bounds.

      Args:
          lower: Lower price boundary
          upper: Upper price boundary
          num_grids: Number of grid levels

      Returns:
          List of price levels in ascending order
      """
  ```
- **Immutability:** Use immutable data structures where possible
  ```python
  # Good
  from dataclasses import dataclass

  @dataclass(frozen=True)
  class Order:
      pair: str
      price: float
      amount: float

  # Avoid
  class Order(dict):
      pass
  ```

## Git Workflow

### Branch Naming

```bash
git checkout -b feature/grid-optimization
git checkout -b fix/order-matching-bug
git checkout -b docs/update-readme
```

Format: `<type>/<description>`

Types:
- `feature/` — New feature
- `fix/` — Bug fix
- `refactor/` — Code refactoring (no behavior change)
- `docs/` — Documentation updates
- `test/` — Test additions/fixes
- `chore/` — Dependency updates, build scripts, etc.

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

<optional body>
```

Examples:
```
feat: add telegram notifications for trade fills

fix: correct grid level rounding to 8 decimals

docs: update README with backtesting examples

test: add unit tests for OrderManager
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

### Pre-commit Checklist

Before committing code:

- [ ] Code passes ruff checks: `ruff check --fix src/`
- [ ] All tests pass: `pytest`
- [ ] Coverage is adequate: `pytest --cov=src --cov-report=term-missing` (80%+)
- [ ] No hardcoded secrets or API keys in code
- [ ] Type hints added to all functions
- [ ] Docstrings added to classes and public functions

### Push and Pull Request

```bash
git push -u origin feature/your-feature-name
```

Then create a PR with:
1. Clear title (matches commit message)
2. Description of changes
3. Link to related issue (if applicable)
4. Test plan / testing instructions

**All PRs require:**
- Tests passing
- Ruff checks passing
- At least one review approval

## Testing Standards

### Minimum Coverage: 80%

All new code must have unit or integration tests. Use the following structure:

### Unit Tests (Fast, Isolated)

Test individual functions and classes with mocks:

```python
import pytest
from src.core.grid_engine import GridEngine

def test_grid_levels():
    engine = GridEngine(
        pair="BTC/USDT",
        lower_price=100.0,
        upper_price=200.0,
        num_grids=5,
        investment=50.0,
    )
    assert len(engine.levels) == 6  # 5 grids + 1 (includes both bounds)
    assert engine.levels[0] == 100.0
    assert engine.levels[-1] == 200.0

def test_investment_validation():
    with pytest.raises(ValueError):
        GridEngine(
            pair="BTC/USDT",
            lower_price=100.0,
            upper_price=200.0,
            num_grids=5,
            investment=-50.0,  # Invalid
        )
```

### Integration Tests (Slower, Full Stack)

Test interactions between components:

```python
@pytest.mark.asyncio
async def test_grid_strategy_places_initial_orders(db, paper_exchange):
    cfg = load_config("config/test.yaml")
    strategy = GridStrategy(
        pair_config=cfg.pairs[0],
        exchange=paper_exchange,
        risk_manager=RiskManager(cfg.risk),
        db=db,
    )

    await strategy.run_once()  # Execute one cycle

    orders = await db.get_open_orders()
    assert len(orders) > 0
```

### Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── test_grid_engine.py            # Core logic
├── test_order_manager.py
├── test_position_tracker.py
├── test_risk_manager.py
├── test_backtester.py
└── fixtures/
    ├── sample_data.py             # Test data
    └── mock_exchange.py           # Mock objects
```

### Using Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
from src.exchange.paper import PaperExchange
from src.storage.database import Database

@pytest.fixture
async def db():
    """In-memory SQLite database for testing."""
    database = Database(connection_string=":memory:")
    await database.connect()
    yield database
    await database.close()

@pytest.fixture
def paper_exchange():
    """Paper trading exchange."""
    return PaperExchange(
        initial_balance=1000.0,
        fee_rate=0.001,
    )
```

## Architecture Guidelines

### Module Organization

Organize code by feature/domain, not by type:

```
Good:
src/core/              # Core trading logic
  grid_engine.py       # Grid level calculation
  order_manager.py     # Order management
  risk_manager.py      # Risk enforcement

Bad:
src/models/           # Avoid grouping by type
src/managers/
src/engines/
```

### Immutability

Use immutable data patterns to prevent hidden side effects:

```python
# Good: Returns new object
def update_order_status(order: Order, new_status: OrderStatus) -> Order:
    return Order(
        id=order.id,
        pair=order.pair,
        side=order.side,
        price=order.price,
        amount=order.amount,
        status=new_status,  # Changed
        grid_level=order.grid_level,
        created_at=order.created_at,
        filled_at=order.filled_at,
        fee=order.fee,
    )

# Better: Use dataclass or Pydantic
order = order.model_copy(update={"status": OrderStatus.FILLED})
```

### Error Handling

Always handle errors explicitly:

```python
# Good: Handle and log
try:
    balance = await exchange.get_balance()
except NetworkError as e:
    logger.error("exchange_connection_failed", error=str(e))
    raise

# Avoid: Silent failures
try:
    balance = await exchange.get_balance()
except:
    pass
```

### Logging

Use structlog for structured, searchable logs:

```python
import structlog

logger = structlog.get_logger()

# Good
logger.info(
    "order_placed",
    pair="BTC/USDT",
    side="buy",
    price=73500.0,
    amount=0.00061,
    grid_level=2,
)

# Avoid
print(f"Order placed: BTC/USDT buy 73500.0 at grid level 2")
```

## Adding a New Feature

### Step 1: Create Issue/Feature Request

Describe the feature and acceptance criteria.

### Step 2: Create Feature Branch

```bash
git checkout -b feature/my-feature
```

### Step 3: Write Tests First (TDD)

```bash
# Create test_new_feature.py
# Write failing tests
pytest tests/test_new_feature.py

# RED: Tests fail
# GREEN: Implement to pass
# IMPROVE: Refactor
```

### Step 4: Implement

Write code to pass tests. Ensure:
- Type hints on all functions
- Docstrings on classes/public functions
- No hardcoded values (use config)
- Structured logging (not print)

### Step 5: Run Full Test Suite

```bash
pytest --cov=src --cov-report=term-missing
```

Must pass with 80%+ coverage.

### Step 6: Lint and Format

```bash
ruff format src/
ruff check --fix src/
```

### Step 7: Create Pull Request

Push and create PR with test results and description.

## Security Checks

Before committing code that touches:
- Authentication / authorization
- User input / validation
- API keys / secrets
- Database queries

Run security checks:

```bash
# Check for common vulnerabilities
ruff check --select=S src/

# Manual review checklist:
# [ ] No hardcoded secrets
# [ ] All user input validated
# [ ] SQL parameterized (not string concatenation)
# [ ] Error messages don't leak sensitive data
# [ ] API keys loaded from environment, not config
```

## Performance Profiling

For optimization work:

```bash
# Profile memory usage
python -m memory_profiler src/core/grid_engine.py

# Profile execution time
python -m cProfile -s cumulative src/main.py run

# Use pytest-benchmark for microbenchmarks
pytest tests/test_benchmarks.py --benchmark-only
```

## Documentation

### Code Comments

Keep comments minimal and meaningful:

```python
# Good: Explains why
async def poll_exchange_prices(self, interval: int):
    # Refresh prices at configured interval to catch grid crossings
    while self._running:
        price = await self.exchange.get_price(self.pair)
        self._current_price = price
        await asyncio.sleep(interval)

# Avoid: States the obvious
result = 0
for order in orders:
    # Add order amount to result
    result += order.amount
```

### Update Documentation When

- Adding new config options → update README and config/default.yaml
- Changing CLI commands → update help text and README
- Adding new environment variables → update .env.example and ENV.md
- Adding new modules → update architecture section of README

## Troubleshooting

### Tests fail on Windows: "ModuleNotFoundError: No module named 'src'"

Set PYTHONPATH:
```bash
$env:PYTHONPATH="."
pytest
```

Or use pytest-pythonpath plugin.

### Import errors after pip install -e .

Reinstall in edit mode:
```bash
pip install -e ".[dev]" --force-reinstall --no-deps
```

### Ruff conflicts with other formatters

Trade Bot uses only ruff. If using VSCode, install the ruff extension and disable black/pylint.

### Need to add a dependency

```bash
pip install new-package
pip freeze > requirements.txt  # or update pyproject.toml manually
```

Then test and commit changes.

## Questions?

Ask in the project Discord/Slack or open a discussion issue.

<!-- END AUTO-GENERATED -->
