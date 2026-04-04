# ccTracker

ccTracker is a small Python app for tracking credit card benefits and stay-related progress from transaction data. It focuses on the core business logic for calculating benefits and summarizing activity.

## Bilt Cash Tracker

The app includes a Bilt cash projection tracker for the current calendar year.

Inputs:
- Bilt cash earned so far (dollars)
- Fixed monthly mortgage payment to put on the card for the remaining months in the year

Assumptions:
- Uses only currently earned Bilt cash (no future cash earning projection)
- Redemption is linear at $0.03 Bilt cash per $1 mortgage spend
- Bilt cash expires on Dec 31 with up to $100 rollover

Outputs include projected cash usage by year-end, mortgage dollars used, remaining cash, rollover amount, and warning when projected expiration is above $0.

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
