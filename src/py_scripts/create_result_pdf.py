import spacy
from spacy.tokens import Doc, Token, Span, SpanGroup, DocBin
from spacy import displacy
import pdfkit
import pyjq
import pandas as pd
import json
import sys
import os
import argparse
import pprint

pd.options.display.max_colwidth = 0 
pd.options.display.max_columns = None
pd.set_option('display.width', 1000)
pp = pprint.PrettyPrinter(width=150, compact=True)


nlp = None


#register token-level and span-level extensions in Spacy
try:
    #to deserialize docbin we need to set these again
    Token.set_extension("bner", default = []) 
    Token.set_extension("IS_BODY_ORGAN", default = 0)
    Token.set_extension("IS_MEDICATION", default = 0)
    Token.set_extension("IS_DISEASE", default = 0)
    
    Span.set_extension("IS_MEDICATION", default = 0)
    Span.set_extension("MEDICATION_DETAILS", default = {})
    
    Doc.set_extension("BOOK_PAGE", default = -1)
    
    #were assigned by medspacy context 
    Span.set_extension("is_family_history", default=0)
    Span.set_extension("is_history", default=0)
    Span.set_extension("never_family_history", default=0)
    Span.set_extension("never_history", default=0)
    
    #was set based on dep matcher, on medication ents that have relations to the diseases they are taken for
    Span.set_extension("PURPOSE", default="")

except:
    pass



def prepare_spacy_pipeline():
    """Load English language model"""
    global nlp    
    nlp = spacy.load("en_core_web_lg", disable = ["ner"])
    return

#--------------------------------------------------------------------------

def html_entities_displacy(doc):
    """text with entities highlighted"""
    colors = {"drugbank:MEDICATION_DRUGBANK" : "#fce9a2", "bc5cdr:DISEASE":"#facdee"}
    html_ents_question = displacy.render(doc, style='ent', 
                                         options={"colors":colors}, 
                                         page=True, jupyter=False, minify=True)
    #reduce font in the displacy html
    html_ents_question = html_ents_question.replace("font-size: 16px;", "font-size: 14px;")
    html_ents_question = html_ents_question.replace("margin-bottom: 6rem", "margin-bottom: 1rem")
    #print(html_ents_question)
    return html_ents_question


def html_diseases(doc):
    """align 3 unordered lists of past diseases, family medical history and current health issues"""
    html_diseases = """
        <table style=" border: 1px solid black;border-collapse: collapse;">
            <tr> 
               <th></th>
               <th>Current</th>
               <th>Historic</th>
               <th>Never</th>
            </tr>
    """
    list_diseases = []
    for ent in doc.ents:
        if ent.label_ == "bc5cdr:DISEASE":
            list_diseases.append(ent)
    
    #make them lowercase and remove duplicates in case-insensitive manner
    list_historic = ["<li>" + str(ent.text).lower() + "</li>" for ent in list_diseases if ent._.is_history == 1]
    list_historic = list(set(list_historic))
    ul_historic = "<ul>" + "".join(list_historic) + "</ul>"
    
    list_nothistoric = ["<li>" + str(ent.text).lower() + "</li>" for ent in list_diseases if ent._.never_history == 1]
    list_nothistoric = list(set(list_nothistoric))
    ul_nothistoric = "<ul>" + "".join(list_nothistoric) + "</ul>"
    
    list_family = ["<li>" + str(ent.text).lower() + "</li>" for ent in list_diseases if ent._.is_family_history == 1]
    list_family = list(set(list_family))
    ul_family = "<ul>" + "".join(list_family) + "</ul>"
    
    list_notfamily = ["<li>" + str(ent.text).lower() + "</li>" for ent in list_diseases if ent._.never_family_history == 1]
    list_notfamily = list(set(list_notfamily))
    ul_notfamily = "<ul>" + "".join(list_notfamily) + "</ul>"
    
    list_current = ["<li>" + str(ent.text).lower() + "</li>" for ent in list_diseases 
                    if (ent._.is_history == 0) and (ent._.is_family_history == 0) and \
                       (ent._.never_history == 0) and  (ent._.never_family_history == 0) ]
    list_current = list(set(list_current))
    ul_current = "<ul>" + "".join(list_current) + "</ul>"
    
    html_diseases += """
         <tr>
            <td>Patient</td>
            <td> {ul_crt} </td>
            <td> {ul_his} </td>
            <td> {ul_not} </td>
        </tr>
    """.format( ul_crt = ul_current,
                ul_his = ul_historic,
                ul_not = ul_nothistoric
              )
    
    html_diseases += """
         <tr>
            <td>Patient's Family</td>
            <td> - </td>
            <td> {ul_fam} </td>
            <td> {ul_nofam} </td>
        </tr>
    """.format(
               ul_fam = ul_family,
               ul_nofam = ul_notfamily
              )
    
    html_diseases += "</table>"
    return html_diseases



def html_medication(doc):
    """show in a table the medication mentioned in the text, the DrugBank and RXNORM IDs of these and the diseases they address"""
    html_medication = """
        <table style=" border: 1px solid black;border-collapse: collapse;">
            <tr> 
               <th>Medication</th>
               <th>Purpose</th>
               <th>DrugBank ID</th>
               <th>RxNorm ID</th>
               <th>RxNorm Info</th>
            </tr>
    """
    
    for ent in doc.ents:
        if ent.label_ == "drugbank:MEDICATION_DRUGBANK":
            try:
                rxnorm_link = ent._.MEDICATION_DETAILS["rxnorm_link"]
            except:
                rxnorm_link = ["-","-","-","-","-"]
            
            html_medication += """
            <tr> 
               <td>{text}</td>
               <td>{purpose}</td>
               <td> <a href="https://go.drugbank.com/drugs/{dbid}">{dbid}</a> </td>
               <td>{rxid}</td>
               <td>{rxinfo}</td>
            </tr>""".format(text = ent.text,
                            purpose = ent._.PURPOSE, 
                            dbid = ent._.MEDICATION_DETAILS["drugbank_id"],
                            rxid = rxnorm_link[0],
                            rxinfo = rxnorm_link[4]
                           )
        
    html_medication += "</table>"
    
    return html_medication

#--------------------------------------------------------------------------

def generate_pdf_vignettes(doc_bin, list_cases):
    """For each vignette (i.e. selected page from book in dataset), prepare HTML report and convert it to a PDF file"""
    list_docs = list(doc_bin.get_docs(nlp.vocab))
    list_generated_pdf = []
    FOLDER_REPORTS = "data/vignettes_reports/"
    
    for doc in list_docs:
        pdf_file = "Report_Page_{}.pdf".format(doc._.BOOK_PAGE)
        html_file =  "Report_Page_{}.html".format(doc._.BOOK_PAGE)
        
        html_highlighted_text = html_entities_displacy(doc)
        
        html_diseases_statuses = html_diseases(doc)
        
        html_medication_table = html_medication(doc)
        
        #note: we use double curly baces in the style to escape {, otherwise ued for placeholders
        html_content = """
        <html>
           <head>
               <style>
                    table, th, td {{
                       border: 1px solid black;
                       border-collapse: collapse;
                    }}
                    
                    tr:nth-child(odd)  {{
                      background:rgba(227, 232, 231,0.7);
                    }}
                </style>
           
           </head>
           <body>
               <h2> Clinical vignette of book page {bp}</h2>
               {ents}

                <h3> Health issues</h3>
               {issues}
               
               <h3> Medication</h3>
               {medic}

        </body>
        </html>

        """.format(bp = doc._.BOOK_PAGE,
                   ents = html_highlighted_text, 
                   issues=html_diseases_statuses,
                   medic = html_medication_table
                  )
        
        with open(FOLDER_REPORTS + html_file, "w") as fh:
            fh.write(html_content)
            
        pdfkit.from_file(FOLDER_REPORTS + html_file, FOLDER_REPORTS + pdf_file)
        
        print("Finished generating " + pdf_file)
        list_generated_pdf.append(FOLDER_REPORTS + pdf_file)
        
    return list_generated_pdf
    
    
def main():

    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput1_docbin', action='append', nargs=1)  
    parser.add_argument('--myinput2_ddi', action='append', nargs=1)
    args = parser.parse_args()
    
    #extract inputs into variables
    input1_file = args.myinput1_docbin[0][0]
    input2_file = args.myinput2_ddi[0][0]
        
    _ = prepare_spacy_pipeline()
    
    doc_bin = DocBin().from_disk(input1_file)
    
    with open(input2_file) as f:
        list_cases = json.load(f)        
    
    list_generated_pdf = generate_pdf_vignettes(doc_bin, list_cases)
    
    #now create a file with implicit outputs
    #it must reside in $PROJHOME/.renku/tmp/ , but now we're in $PROJECTHOME/src/py_scripts
    print(os.getcwd())
    with open(".renku/tmp/outputs.txt", "w") as fo:
        for item in list_generated_pdf:
            fo.write("%s\n" %item)
    
    
if __name__ == '__main__':
    main()