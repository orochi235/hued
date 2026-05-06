.PHONY: color-names test

color-names:
	./scripts/generate-names.sh

test:
	bats test/
