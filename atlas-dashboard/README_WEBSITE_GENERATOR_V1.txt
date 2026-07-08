# Atlas Website Generator v1 Audited Files

Copy/merge this ZIP at the repository root:

C:\Atlas\atlas-dashboard

Then run:

```powershell
python -m pytest tests/test_website_generator.py -v
python -m pytest tests -v
```

Included files:

- engines/website_generator/__init__.py
- engines/website_generator/constants.py
- engines/website_generator/models.py
- engines/website_generator/template_engine.py
- engines/website_generator/quality_gate.py
- engines/website_generator/static_site_generator.py
- tests/test_website_generator.py
