⚠️ **Please Note:** This repository documents a tool developed to generate RDF data dumps from an independently run instance of Wikibase. Today, Rhizome recommends that you either run the [Wikibase Docker distribution](https://github.com/wmde/wikibase-docker/) or get a managed Wikibase at [WbStack](https://www.wbstack.com/). If you specifically are looking to get an RDF dump of your Wikibase, [you should use the `dumpRdf.php`](http://learningwikibase.com/install-wikibase/#exporting-data-as-a-json-or-rdf-dump), which is supplied with Wikibase.

---

# Bringing ✨ to Wikibase

This Python 3 script converts entities from a local Wikibase to RDF (turtle format), ready to be imported into a Blazegraph graph database. It attemps to use the same data structure as Wikidata.

## Environment

The script expects login credentials to the MySQL/MariaDB instance used by the local Wikibase in environment variables:

|environment variable|expected value             |
|--------------------|---------------------------|
|`wbdbhost`          |MySQL/MariaDB Host         |
|`wbdbuser`          |MySQL/MariaDB user name    |
|`wbdbpasswd`        |MySQL/MariaDB user password|
|`wbdbdb`            |Name of database           |

## Usage

`./web2ttl.py [-e <exactMatchProperty>] <localBase> <outfile>`

With the optional switch `-e` it is possible to designate a local Wikibase property to be treated as `skos:exactMatch`. This allows to match local properties with Wikidata properties or any other graph.

The option `-e P2` would use the local property P2. For example, in Rhizome's Wikibase, the property [P3 (instance of)](https://catalog.rhizome.org/w/Property:P3) is matched with P31 (instance of) on Wikidata and rdf:instance of.

The `local_base` paramter defines the local URI prefix. In Rhizome's case, this is `http://catalog.rhizome.org/`.

`outfile` is where the RDF output will go.

## Updating Blazegraph

Given that Wikibase and Blazegraph are running on the same host, a script like this will export the RDF from Wikibase, clear any data in Blazegraph, and then import the new graph:

```bash
#!/bin/bash

export wbdbhost=localhost
export wbdbuser=alice       # MySQL/MariaDB user name
export wbdbpasswd=sikrit    # password 
export wbdbdb=wiki          # name of database

./wb2ttl.py -e P2 http://catalog.rhizome.org/ db-export.ttl

chmod a+r db-export.ttl

ABSFILE=`readlink -f db-export.ttl`

curl "http://localhost:9999/blazegraph/namespace/kb/sparql"  --data-urlencode "update=DROP ALL; LOAD <file:///$ABSFILE>;"
```

This script could be run as a cronjob for reglar updates.

## Deployment at Rhizome

See [presentation](https://docs.google.com/presentation/d/1rfohNJ9FcUZuhMAzatbISAJlIj-aTMBAzDWMGl3vGr0/edit?usp=sharing) (Google Slides) from [WikidataCon 2017](https://www.wikidata.org/wiki/Wikidata:WikidataCon_2017/Submissions/Integrating_a_custom_Wikibase_Instance_(Rhizome)_and_Wikidata_via_SPARQL)
