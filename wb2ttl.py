#!/usr/bin/env python3

""" Convert Wikibase Items and Properties to RDF.
    Tested with Wikibase DataModel 6.3.0.
    Requires environment variables to be set:
        wbdbhost:   MySQL/MariaDB Host
        wbdbuser:   MySQL/MariaDB user name
        wbdbpasswd: MySQL/MariaDB user password
        wbdbdb:     Name of database
"""

from os import environ
import uuid
from pprint import pprint
import pymysql.cursors
import json
from rdflib import Namespace, Graph, URIRef, BNode, Literal
from rdflib.namespace import DCTERMS, RDFS, RDF, DC, SKOS, OWL, XSD
import sys
from argparse import ArgumentParser
import traceback

argparser = ArgumentParser('Translate Wikibase into TTL, based on the Wikidata DataModel 6.3.0.')
argparser.add_argument('local_base', help='Base URI')
argparser.add_argument('outfile', help='Filename to write TTL to')
argparser.add_argument('-e', '--exactMatch', help='Wikibase property that is equivalent with skos:exactMatch', default=False)
options = argparser.parse_args()


# Set the namespaces
# Here we are trying to replicate the exact same structure as in Wikidata
wikidata_base = "http://www.wikidata.org/"

# Mint local namespace
wdp = Namespace("prop/")
rhp = Namespace(options.local_base+"prop/")

wdwdt = Namespace(wikidata_base+"prop/direct/")
rhwdt = Namespace(options.local_base+"prop/direct/")

wdwd = Namespace(wikidata_base+"entity/")
rhwd = Namespace(options.local_base+"entity/")

wdref = Namespace(wikidata_base+"reference/")
rhref = Namespace(options.local_base+"reference/")

wds = Namespace(wikidata_base+"entity/statement/")
rhs = Namespace(options.local_base+"entity/statement/")

wdps = Namespace(wikidata_base+"prop/statement/")
rhps = Namespace(options.local_base+"prop/statement/")

wdpr = Namespace(wikidata_base+"prop/reference/")
rhr = Namespace(options.local_base+"prop/reference/")

wdpq = Namespace(wikidata_base+"prop/qualifier/")
rhq = Namespace(options.local_base+"prop/qualifier/")

wikibase = Namespace("http://wikiba.se/ontology#")

# Remote namespaces
wikibase = Namespace("http://wikiba.se/ontology#")
schema = Namespace("http://schema.org/")
prov = Namespace("http://www.w3.org/ns/prov#")

# Define the rhizomeGraph
rhizomeGraph = Graph()
rhizomeGraph.bind("schema", schema)
rhizomeGraph.bind("skos", SKOS)
rhizomeGraph.bind("wikibase", wikibase)


connection = pymysql.connect(
    host=environ['wbdbhost'],
    user=environ['wbdbuser'],
    password=environ['wbdbpasswd'],
    db=environ['wbdbdb'],
    cursorclass=pymysql.cursors.DictCursor
)

# Read SQL queries
sql_getjson = open('get-json.sql', 'r').read(); # to get entities as json
sql_propinfo = open('property-info.sql', 'r').read(); # to get type info on property

try:
    with connection.cursor() as cursor_properties:
        cursor_properties.execute(sql_propinfo)
        propinfo_results = cursor_properties.fetchall()  
finally:
    pass

# Convert property info into dictionary, so the type of a property can be easily
# checked. Example:
#   propinfo['P2'] -> 'url'
propinfo = {}
for pi in propinfo_results:
    if 'type' in pi.keys():
        propinfo[pi['id']] = pi['type']
    else:
        print('Error: Missing data type information for property {0} in database table wb_property_info.'.format(pi['id']))
        exit()

try:
    with connection.cursor() as cursor_entities:
        cursor_entities.execute(sql_getjson)
finally:
    pass

for row in cursor_entities:
    j = json.loads(row['json_text'])

    j['modified'] = row['modified']
    
    id = j['id'] # P or Q identifier
    
    isProperty = (id[0] == 'P')

    rhizomeGraph.add((rhwd[id], RDFS.label, Literal(j['labels']['en']['value'], lang='en')))

    if 'en' in j['descriptions']:
        rhizomeGraph.add((rhwd[id], schema.description, Literal(j['descriptions']['en']['value'], lang='en')))

    if isProperty:
        rhizomeGraph.add((rhwd[id], RDF.type, wikibase.Property))
        rhizomeGraph.add((rhwd[id], wikibase.directClaim, rhwdt[id]))
        rhizomeGraph.add((rhwd[id], wikibase.claim, rhp[id]))
    
    # walk all claims
    for claim_prop in j['claims']:
        if claim_prop not in propinfo:
            print('Property {0} not available in database table wb_property_info.'.format(claim_prop))
            exit()
            
        for claim in j['claims'][claim_prop]:

            # walk all statements
            for statement in j['claims'][claim_prop]:
                statementNode = rhs[statement['id']] # extract unique ID for statement node
                rhizomeGraph.add((rhwd[id], rhp[claim_prop], statementNode))
                
                try:
                    datavalue = statement['mainsnak']['datavalue']

                    # - - - translate each wikibase datatype to ttl - - -

                    if claim_prop not in propinfo:
                        print('Error: No information about Property {0} available (at entity {1})'.format(prop_info, id))
                        exit()

                    # matching local exactMatch with SKOS
                    if claim_prop == options.exactMatch:
                        rhizomeGraph.add((
                            rhwd[id],
                            SKOS.exactMatch, 
                            URIRef(datavalue['value'])
                        ))
                        # output to validate that exactMatch is being applied
                        print('{0} -> {1}'.format(rhwd[id], datavalue['value']))


                    #regular statements
                         
                    if propinfo[claim_prop] == 'wikibase-item':
                        rhizomeGraph.add((
                            rhwd[id],
                            rhwdt[claim_prop],
                            URIRef(rhwd['Q' + str(datavalue['value']['numeric-id']) ])
                        ))
                        rhizomeGraph.add((
                            statementNode,
                            rhps[claim_prop],
                            URIRef(rhwd['Q' + str(datavalue['value']['numeric-id'])])
                        ))

                    elif propinfo[claim_prop] == 'string':
                        rhizomeGraph.add((
                            rhwd[id],
                            rhwdt[claim_prop],
                            Literal(datavalue['value'])
                        ))
                        rhizomeGraph.add((
                            statementNode,
                            rhps[claim_prop],
                            Literal(datavalue["value"])
                        ))

                    # TODO: revisit commonsMedia
                    elif propinfo[claim_prop] == 'commonsMedia':
                        rhizomeGraph.add((
                            rhwd[id], 
                            rhwdt[claim_prop],
                            Literal(datavalue['value'])
                        ))
                        rhizomeGraph.add((
                            statementNode,
                            rhps[claim_prop],
                            Literal(datavalue['value'])
                        ))

                    elif propinfo[claim_prop] == 'url':
                        rhizomeGraph.add((
                            rhwd[id],
                            rhwdt[claim_prop],
                            URIRef(datavalue['value'])
                        ))
                        rhizomeGraph.add((
                            statementNode, 
                            rhps[claim_prop],
                            URIRef(datavalue['value'])
                        ))

                    elif propinfo[claim_prop] == 'time':
                        rhizomeGraph.add((
                            rhwd[id],
                            rhwdt[claim_prop],
                            Literal(datavalue['value']['time'], datatype=XSD.dateTime)
                        ))
                        rhizomeGraph.add((
                            statementNode,
                            rhps[claim_prop],
                            Literal(datavalue['value']['time'], datatype=XSD.dateTime)
                        ))

                    # references
                    if 'references' in statement:
                        for reference in statement["references"]:
                            referenceNode = rhref[str(uuid.uuid4())]
                            rhizomeGraph.add((
                                statementNode, 
                                prov['wasDerivedFrom'], 
                                referenceNode
                            ))
                            for snakProperty in reference['snaks']:
                                for snak in reference['snaks'][snakProperty]:
                                    if snak['datavalue']['type'] == 'url':
                                        rhizomeGraph.add((
                                            referenceNode,
                                            rhr[snak['property']],
                                            URIRef(snak['datavalue']['value'])
                                        ))
                                    elif snak['datavalue']['type'] == 'string':
                                        rhizomeGraph.add((
                                            referenceNode,
                                            rhr[snak['property']], 
                                            Literal(snak['datavalue']['value'])
                                        ))
                                    elif snak['datavalue']['type'] == 'time':
                                        rhizomeGraph.add((
                                            referenceNode,
                                            rhr[snak['property']],
                                            Literal(snak['datavalue']['value']['time'])
                                        ))

                    # qualifiers
                    if 'qualifiers' in statement.keys():
                        for qualifier in statement['qualifiers']:
                            for snak in statement['qualifiers'][qualifier]:
                                if snak['datavalue']['type'] == 'quantity':
                                    rhizomeGraph.add((
                                        statementNode,
                                        rhq[snak['property']],
                                        Literal(snak['datavalue']['value']['amount'])
                                    ))


                except KeyError as e:
                    traceback.print_exc()
                    print('KeyError', e)
                    print('ID: {id}, CLAIM: {claim_prop}'.format(id=id, claim_prop=claim_prop))
                    pprint(statement)
                    exit()


connection.close()      
        
# Export final results
rhizomeGraph.serialize(destination=options.outfile, format='turtle')
            
