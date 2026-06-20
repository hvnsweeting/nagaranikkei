.PHONY: test test-v build lint secrets update-expect precommit clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

test: ## Run test suite
	python test_build.py

test-v: ## Run test suite (verbose)
	python test_build.py -v

build: ## Run the static site generator
	python build.py

lint: ## Run mypy strict type checking
	mypy --strict build.py test_build.py parser.py history.py models.py utils.py analyzer.py templates.py rss_generator.py

format: ## Run black code formatter
	black build.py test_build.py parser.py history.py models.py utils.py analyzer.py templates.py rss_generator.py

secrets: ## Run gitleaks secrets scan
	gitleaks detect --no-git --source . --verbose --redact

update-expect: ## Update expect/snapshot test baselines
	UPDATE_EXPECT=1 python test_build.py

precommit: lint test secrets ## Run all pre-commit checks (lint + test + secrets)

clean: ## Remove generated dist output
	rm -rf dist
