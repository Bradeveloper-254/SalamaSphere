# Automated test report

- Command: `python -m pytest -q`
- Environment: project `.venv`, Python 3.14.3, pytest 9.2.0
- Result: **10 passed**
- Coverage includes artifact loading, preprocessing of invalid Unicode, valid Kiswahili and Sheng-like input schema, empty/None/non-string input, long-input truncation, and threshold application.

No automated test uses the held-out test dataset or calls an external service.
