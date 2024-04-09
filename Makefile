RUN = poetry run
CODE = src/go_db
DM = $(CODE)/datamodel

all: datamodel test trigger integration-test

datamodel: $(DM)/biblio.py

test: pytest doctest


pytest:
	$(RUN) pytest

doctest:
	$(RUN) python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE $(CODE)/*.py

%-doctest: %
	$(RUN) python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE $<


$(DM)/%.py: $(DM)/%.yaml
	$(RUN) gen-pydantic --pydantic-version 2 $< > $@.tmp && mv $@.tmp $@


trigger:
	touch tests/input/cjm.paperpile.csv
integration-test: tests/output/cjm.html

tests/output/%.json: tests/input/%.paperpile.csv
	$(RUN) go_db export --repair -a "Mungall CJ?" --annotate-position -i $< -O json -o $@
.PRECIOUS: tests/output/%.json

tests/output/%-merged.json: tests/output/%.json tests/input/cjm.roles.csv
	$(RUN) go_db merge -i $< -f json -s bibm -m tests/input/cjm.roles.csv -c role -O json -o $@
.PRECIOUS: tests/output/%-merged.json


tests/output/%.md: tests/output/%-merged.json $(CODE)/templates/default.markdown.jinja2
	$(RUN) go_db export -f json -s bibm  --repair -a "Mungall CJ?" --annotate-position -i $< -O markdown -o $@

tests/output/%.html: tests/output/%.md
	pandoc $< -o $@

#src/go_db/datamodel/z2cls-typeMap.xml: https://aurimasv.github.io/z2csl/typeMap.xml
#	curl -L -s $< > $@
