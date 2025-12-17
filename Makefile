RUN = poetry run
CODE = src/go_db
DM = $(CODE)/datamodel
DBS = filtered_goa_uniprot_all
OBO = http://purl.obolibrary.org/obo

# NCBITaxon IDs for common organisms
TAXON_VIRUS = NCBITaxon:10239
TAXON_BACTERIA = NCBITaxon:2
TAXON_ARCHAEA = NCBITaxon:2157
TAXON_FUNGI = NCBITaxon:4751
TAXON_HUMAN = NCBITaxon:9606
TAXON_PLANT = NCBITaxon:33090
TAXON_MAMMALIA = NCBITaxon:40674
TAXON_EUKARYA = NCBITaxon:2759
TAXON_PSEUDOMONADOTA = NCBITaxon:1224
TAXON_CLOSTRIDIUM = NCBITaxon:186801
TAXON_PSEPK = NCBITaxon:160488 # Pseudomonas putida KT2440
TAXON_ANOGA = NCBITaxon:7165 # Anopheles gambiae
TAXON_ZIKV = NCBITaxon:64320 # Zika virus

GCRP_DB = db/goa_uniprot_gcrp.ddb

# Source database - default to GCRP for comprehensive coverage including viruses
SOURCE_DB ?= $(GCRP_DB)

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
	$(RUN) go-db load -d $@ -g db/go.db $<

db/%_lite.ddb: data/gaf/%.gaf.gz
	$(RUN) go-db load -d $@ $<

# ensure all of NCBITaxon loaded to allow filtering
db/goa_uniprot_%.ddb: data/gaf/goa_uniprot_%.gaf.gz
	$(RUN) go-db load -d $@ -g db/go.db -s db/ncbitaxon.db $<


#data/gaf/%.gaf:
#	curl -L -s  https://current.geneontology.org/annotations/$*.gaf.gz | gzip -dc > $@.tmp && mv $@.tmp $@

data/gaf/goa_uniprot_%.gaf.gz:
	curl -L -s  https://ftp.ebi.ac.uk/pub/databases/GO/goa/UNIPROT/goa_uniprot_$*.gaf.gz > $@.tmp && mv $@.tmp $@
.PPRECIOUS: data/gaf/goa_uniprot_%.gaf.gz

data/gaf/pombase_new.gaf.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/gaf/SCHPO_4896_UP000002485.gaf.gz  > $@.tmp && mv $@.tmp $@

data/gaf/pombase_orig.gaf.gz:
	curl -L -s https://www.pombase.org/data/annotations/Gene_ontology/gene_association.pombase.gz  > $@.tmp && mv $@.tmp $@

data/gaf/ZIKV.gaf.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/gaf/ZIKV_64320_UP000054557.gaf.gz > $@.tmp && mv $@.tmp $@

data/gaf/ANOGA.gaf.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/gaf/ANOGA_7165_UP000007062.gaf.gz > $@.tmp && mv $@.tmp $@

data/gaf/BRADI.gaf.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/gaf/BRADI_15368_UP000008810.gaf.gz > $@.tmp && mv $@.tmp $@

data/gaf/SCHPO.gaf.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/contrib/goa/goex/current/gaf/SCHPO_4896_UP000002485.gaf.gz > $@.tmp && mv $@.tmp $@

data/gaf/%.gaf.gz:
	curl -L -s  https://current.geneontology.org/annotations/$*.gaf.gz > $@.tmp && mv $@.tmp $@



data/gpi/uniprot_reviewed.gpi:
	curl -L -s http://ftp.ebi.ac.uk/pub/contrib/goa/uniprot_reviewed.gpi.gz | gzip -dc > $@

data/gpi/gcrp.gpi.gz:
	curl -L -s https://ftp.ebi.ac.uk/pub/databases/GO/goa/UNIPROT/goa_uniprot_gcrp.gpi.gz > $@


# ================================================================================
# SEMSQL
# ================================================================================
data/owl/go.owl:
	robot merge -I $(OBO)/go/extensions/go-plus.owl -I $(OBO)/ncbitaxon.owl -o $@

db/go.db:
	cp ~/.data/oaklib/go.db $@


# ================================================================================
# TAXON-SPECIFIC EXPORT TARGETS
# ================================================================================

# Export GAF files for specific taxa using taxon closure
# These targets extract all annotations for a taxon and its descendants

# bacteria, archaea, fungi - extract from GCRP database using taxon closure

data/gaf/bacteria.gaf: $(GCRP_DB)
	@mkdir -p data/gaf
	@echo "Exporting bacteria annotations from GOA GCRP..."
	$(RUN) go-db export -d $(GCRP_DB) --taxon-closure=$(TAXON_BACTERIA) -o $@

data/gaf/archaea.gaf: $(GCRP_DB)
	@mkdir -p data/gaf
	@echo "Exporting archaea annotations from GOA GCRP..."
	$(RUN) go-db export -d $(GCRP_DB) --taxon-closure=$(TAXON_MAMMALIA) -o $@

data/gaf/mammal.gaf: $(GCRP_DB)
	@mkdir -p data/gaf
	@echo "Exporting mammal annotations from GOA GCRP..."
	$(RUN) go-db export -d $(GCRP_DB) --taxon-closure=$(TAXON_ARCHAEA) -o $@

data/gaf/fungi.gaf: $(GCRP_DB)
	@mkdir -p data/gaf
	@echo "Exporting fungi annotations from GOA GCRP..."
	$(RUN) go-db export -d $(GCRP_DB) --taxon-closure=$(TAXON_FUNGI) -o $@

data/gaf/pseudomonadota.gaf: $(SOURCE_DB)
	@mkdir -p data/gaf
	@echo "Exporting Pseudomonadota annotations from $(SOURCE_DB)..."
	$(RUN) go-db export -d $(SOURCE_DB) --taxon-closure=$(TAXON_PSEUDOMONADOTA) -o $@

data/gaf/clostridium.gaf: $(SOURCE_DB)
	@mkdir -p data/gaf
	@echo "Exporting Clostridium annotations from $(SOURCE_DB)..."
	$(RUN) go-db export -d $(SOURCE_DB) --taxon-closure=$(TAXON_CLOSTRIDIUM) -o $@

# note in GO reference species, so extract from GCRP
data/gaf/PSEPK.gaf: $(GCRP_DB)
	@mkdir -p data/gaf
	$(RUN) go-db export -d $(GCRP_DB) --taxon-closure=$(TAXON_PSEPK) -o $@

data/gaf/plant.gaf: $(SOURCE_DB)
	@mkdir -p data/gaf
	@echo "Exporting plant annotations for NCBITaxon:33090 from GOA GCRP..."
	$(RUN) go-db export -d $(SOURCE_DB) --taxon-closure=$(TAXON_PLANT) -o $@

# viruses not in GCRP
data/gaf/virus.gaf: db/goa_uniprot_all.ddb
	@mkdir -p data/gaf
	@echo "Exporting virus from non-GCRP..."
	$(RUN) go-db export -d $(SOURCE_DB) --taxon-closure=$(TAXON_VIRUS) -o $@

# Generic rule for any taxon - usage: make data/gaf/taxon_12345.gaf
data/gaf/taxon_%.gaf: $(SOURCE_DB)
	@mkdir -p data/gaf
	@echo "Exporting annotations for NCBITaxon:$* from $(SOURCE_DB)..."
	$(RUN) go-db export -d $(SOURCE_DB) --taxon-closure=NCBITaxon:$* -o $@

# ================================================================================
# DATABASE CREATION FROM GAF FILES
# ================================================================================

# Create specialized databases from GAF files
# These targets load GAF files into new DuckDB databases

db/virus.ddb: data/gaf/virus.gaf
	@echo "Creating virus database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

db/bacteria.ddb: data/gaf/bacteria.gaf
	@echo "Creating bacteria database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

db/archaea.ddb: data/gaf/archaea.gaf
	@echo "Creating archaea database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

db/fungi.ddb: data/gaf/fungi.gaf
	@echo "Creating fungi database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

db/plant.ddb: data/gaf/plant.gaf
	@echo "Creating plant database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<


db/pseudomonadota.ddb: data/gaf/pseudomonadota.gaf
	@echo "Creating Pseudomonadota database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

db/clostridium.ddb: data/gaf/clostridium.gaf
	@echo "Creating Clostridium database..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

# Generic rule for any taxon database - usage: make db/taxon_12345.ddb
db/taxon_%.ddb: data/gaf/taxon_%.gaf
	@echo "Creating database for taxon $*..."
	$(RUN) go-db load -d $@ -f --go-db-path db/go.db $<

# ================================================================================
# CONVENIENCE TARGETS
# ================================================================================

# Shortcuts for common operations
gcrp: $(GCRP_DB)
virus: db/virus.ddb
bacteria: db/bacteria.ddb
archaea: db/archaea.ddb
fungi: db/fungi.ddb
plant: db/plant.ddb
human: db/goa_human.ddb

# Export all major kingdom GAFs
export-kingdoms: data/gaf/bacteria.gaf data/gaf/archaea.gaf data/gaf/fungi.gaf

# Create all major kingdom databases
build-kingdoms: db/bacteria.ddb db/archaea.ddb db/fungi.ddb

# Clean generated files
clean-gaf:
	rm -f data/gaf/virus.gaf data/gaf/bacteria.gaf data/gaf/archaea.gaf data/gaf/fungi.gaf data/gaf/taxon_*.gaf

clean-taxon-db:
	rm -f db/virus.ddb db/bacteria.ddb db/archaea.ddb db/fungi.ddb db/goa_human.ddb db/taxon_*.ddb $(GCRP_DB)

.PHONY: gcrp virus bacteria archaea plant fungi human export-kingdoms build-kingdoms clean-gaf clean-taxon-db
