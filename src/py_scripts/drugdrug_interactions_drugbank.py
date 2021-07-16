import requests
import pandas as pd
import json
import sys
import argparse
import itertools
from tabulate import tabulate
import pprint
import warnings
from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.simplefilter('ignore',InsecureRequestWarning)
pp = pprint.PrettyPrinter(width=150, compact=True)

def postprocess_sparql_result(res_json):
    """restructure sparql query response"""
    result_json = []
    
    for item in res_json["results"]["bindings"]:
        interaction_info = item["titleddi_str"]["value"]
        drug1_id =  item["d1_str"]["value"]
        drug2_id =  item["d2_str"]["value"]
        drug1_name =  item["drug1_label_str"]["value"]
        drug2_name =  item["drug2_label_str"]["value"]        
        
        result_json.append({"interaction": interaction_info,
                           "drug1_id" : drug1_id,
                           "drug2_id" : drug2_id,
                           "drug1_name" : drug1_name,
                           "drug2_name" : drug2_name })                     
    
    return result_json



def sparql_query_bio2rdf_interactions(drugbank_id1, drugbank_id2 = None, debug_flag = False):
    """send query to Bio2RDF Virtuoso server and parse results to find out either:
    -  all interactions for a given medication  (when drugbank_id2 = None)
    -  interaction between a pair of specified medicines (drugbank_id1, drugbank_id2)
    """
    
    sparql_url = "https://drugbank.bio2rdf.org/sparql"
    
    line_value_id1 = "VALUES ?db_drug1 {db:" + drugbank_id1 + "} ."
    if drugbank_id2 is None:
        line_value_id2 = ""
    else:
        line_value_id2 = "VALUES ?db_drug2 {db:" + drugbank_id2 + "} ."
        
    qq = """
    PREFIX db: <http://bio2rdf.org/drugbank:>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX dv: <http://bio2rdf.org/drugbank_vocabulary:>
    PREFIX bv: <http://bio2rdf.org/bio2rdf_vocabulary:>

    SELECT DISTINCT ?d1_str ?drug1_label_str ?d2_str ?drug2_label_str ?titleddi_str
    WHERE {""" + \
        line_value_id1 + "\n" + \
        line_value_id2 + "\n" + \
    """
        ?db_drug1 rdf:type dv:Drug;
                  bv:identifier ?d1;
                  dct:title ?drug1_label;
                  dv:ddi-interactor-in ?interactor.

        ?db_drug2 rdf:type dv:Drug; 
                  bv:identifier ?d2;
                  dct:title ?drug2_label;
                  dv:ddi-interactor-in ?interactor.

        ?interactor dct:title ?titleddi.

        BIND(STR(?titleddi) AS ?titleddi_str).  
        BIND(STR(?d1) AS ?d1_str).
        BIND(STR(?d2) AS ?d2_str).    
        BIND(STR(?drug1_label) AS ?drug1_label_str).
        BIND(STR(?drug2_label) AS ?drug2_label_str).    

    }
    OFFSET 0
    """
    
    #print(qq)
    
    r = requests.get(sparql_url, 
                     params={"query":qq}, 
                     headers={"Accept":"application/sparql-results+json"}, 
                     verify = False)
    res_json = json.loads(r.content) 
    
    #if debug_flag is True:
        #pp.pprint(res_json)
        #print("--------------------------------------------------------")
        
    result_json = postprocess_sparql_result(res_json) 
    df_result = pd.DataFrame(result_json)
    
    if debug_flag is True:    
        print(df_result.head(5))
        
    return result_json
    
    
    

def query_drugs_interactions(list_cases):
    """for each clinical case for which medication was annotated in a previous step of the workflow,
       form all pairs among the medicines taken by the patient and record interactions between these drugs 
    """
    list_cases_augm = []
    
    for medication_vignette in list_cases:
        ddi = []
        
        #extract unique medication ids in the question
        list_ids = [item["drugbank_id"] for item in medication_vignette["bner_question"]]
        list_uniq_ids = list(set(list_ids))
        #generate all combinations of the items in the set
        list_pairs = list(itertools.combinations(list_uniq_ids, 2))
        for pair_drugs in list_pairs:
            result_json = sparql_query_bio2rdf_interactions( pair_drugs[0], pair_drugs[1])
            if (len(result_json) > 0):  
                #since we asked for a pair, there is only one item in the list result_json
                ddi.extend(result_json)
                
        medication_vignette.update({"drugdrug_interactions": ddi}) 
        list_cases_augm.append(medication_vignette)

    return list_cases_augm
    
    
    
def main():
    
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=1)
    parser.add_argument('--myoutput', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    medication_json = args.myinput[0][0]
    target_file = args.myoutput[0][0]
        
    with open(medication_json) as f:
        list_cases = json.load(f)
    
    list_cases_augm = query_drugs_interactions(list_cases)
    
    #dump outputs to json files
    with open(target_file, "w") as fo:
        json.dump(list_cases_augm, fo)
        
        
if __name__ == '__main__':
    main()
