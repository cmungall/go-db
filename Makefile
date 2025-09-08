RUN = poetry run
CODE = src/go_db
DM = $(CODE)/datamodel
DBS = filtered_goa_uniprot_all

all: datamodel test trigger integration-test

datamodel: $(DM)/biblio.py

test: pytest doctest


pytest:
	$(RUN) pytest

doctest:
	$(RUN) python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE $(CODE)/*.py

%-doctest: %
	$(RUN) python -m doctest --option ELLIPSIS --option NORMALIZE_WHITESPACE $<

db/%.ddb: data/gaf/%.gaf.gz
	$(RUN) go-db load -d $@ $< 

#data/gaf/%.gaf:
#	curl -L -s  https://current.geneontology.org/annotations/$*.gaf.gz | gzip -dc > $@.tmp && mv $@.tmp $@

data/gaf/goa_uniprot_%.gaf.gz:
	curl -L -s  https://ftp.ebi.ac.uk/pub/databases/GO/goa/UNIPROT/goa_uniprot_$*.gaf.gz > $@.tmp && mv $@.tmp $@
.PPRECIOUS: data/gaf/goa_uniprot_%.gaf.gz


data/gaf/%.gaf.gz:
	curl -L -s  https://current.geneontology.org/annotations/$*.gaf.gz > $@.tmp && mv $@.tmp $@



data/gpi/uniprot_reviewed.gpi:
	curl -L -s http://ftp.ebi.ac.uk/pub/contrib/goa/uniprot_reviewed.gpi.gz | gzip -dc > $@

data/gpi/gcrp.gpi.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/databases/GO/goa/UNIPROT/goa_uniprot_gcrp.gpi.gz > $@
