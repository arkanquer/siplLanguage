# REL-01 acceptance evidence

1. Push the `.github/workflows/ci.yml` file to a GitHub repository with Actions enabled.
2. In **Actions → SIPL CI**, confirm both Python versions have green jobs.
3. Open a pull request and verify it triggers the same workflow.
4. Inspect the steps: Ruff lint, mypy types, pytest, Conformance suite, distribution build.
5. Download `sipl-python-distributions` and confirm `.whl` and `.tar.gz` files are present.
6. Add an Actions badge to README after your repository owner/name are known:
   `![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)`.

The lint rule set deliberately checks critical errors rather than full style.
Type checks currently cover the annotated AST and trace models only.
