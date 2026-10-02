# From https://github.com/geneontology/operations/tree/master/docker/amigo-standalone
mkdir -p /tmp/srv-solr-data/index
docker run -p 8080:8080 -p 9999:9999 -v /tmp/srv-solr-data:/srv/solr/data -t geneontology/amigo-standalone
