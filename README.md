# ccTracker

ccTracker is a small Python app for tracking credit card benefits and stay-related progress from transaction data. It focuses on the core business logic for calculating benefits and summarizing activity.

## Installation

Install test dependencies:

```bash
pip install -r requirements.txt
```

## Development

### Running Tests

Run all tests:
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest test_card_processor.py
pytest test_benefits_calculator.py
pytest test_stays_manager.py
```

Run specific test class:
```bash
pytest test_card_processor.py::TestPersonalCardBonusNights
```

Run specific test:
```bash
pytest test_card_processor.py::TestPersonalCardBonusNights::test_first_tier_crossing
```

Run with coverage report:
```bash
pytest --cov=. --cov-report=html
```
