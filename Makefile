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

data/gpi/uniprot_reviewed.gpi:
	curl -L -s http://ftp.ebi.ac.uk/pub/contrib/goa/uniprot_reviewed.gpi.gz | gzip -dc > $@

data/gpi/gcrp.gpi.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/databases/GO/goa/UNIPROT/goa_uniprot_gcrp.gpi.gz > $@
