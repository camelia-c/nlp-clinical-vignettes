from tika import parser
import json
import sys
import argparse

def parse_pdf_content(book_pdf):
    """extract book's PDF content as list of pages, which can be processed individually"""

    parsed_pdf = parser.from_file(book_pdf, xmlContent=True)

    body = parsed_pdf['content'].split('<body>')[1].split('</body>')[0]
    body_without_tag = body.replace("<p>", "").replace("</p>", "").replace("<div>", "").replace("</div>","").replace("<p />","")

    book_individual_pages = body_without_tag.split("""<div class="page">""")[1:]

    return book_individual_pages

#----------------------------------------------------------------------------------

def extract_case(book_individual_pages, page_id):
    """extract question on book page specified by page_id and extract its answer from the following page """
    
    page_question = book_individual_pages[page_id].replace("\n"," ")
    page_answer = book_individual_pages[page_id + 1].replace("\n"," ")

    #the question limits
    question_start = page_question.find("Question:")
    question_end = page_question.find("Contributors:")

    question_txt = page_question[question_start + len("Question:"): question_end].strip()

    #-- now the answer limits
    answer_start = page_answer.find("Answer:")
    answer_end = page_answer.find(" Take Home Points")

    answer_txt = page_answer[answer_start + len("Answer:"): answer_end].strip()

    res = {"question" : question_txt, "answer" : answer_txt , "book_page": page_id}
    return res

#----------------------------------------------------------------------------------

def extract_selected_cases(book_individual_pages, list_pages_to_read):
    """iterate the selected pages numbers in list_pages_to_read, apply processing and collect
       results into a list of dicts. Inexistant page numbers are collected separately in a list of errors"""

    list_cases = []
    list_errors = []
    
    for page_id in list_pages_to_read:
        try:
            current_case = extract_case(book_individual_pages, page_id)
            list_cases.append(current_case)
        except Exception as e:
            list_errors.append({"book_page" : page_id, "error": str(e)})

    dict_results = {"vignettes" : list_cases,
                    "errors" : list_errors                    
                   }
    return dict_results

#----------------------------------------------------------------------------------

def main():
     #print(sys.argv) ###['src/py_scripts/extract_book_pages.py', '--myinput', 'data/book_clinical_cases/JMD-Cases-of-Interest.pdf', 'data/tmp_files/pages_selection.txt', '--myoutput', 'data/outputs/vignettes_selection1.json', '--errors', 'data/errors/errors_selection1.json']
        
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('--myinput', action='append', nargs=2,  metavar=('bookpdf','selected_pages'))
    parser.add_argument('--myoutput', action='append', nargs=1)
    parser.add_argument('--errors', action='append', nargs=1)
    args = parser.parse_args()
    
    #print(args) ###Namespace(errors=[['data/errors/errors_selection1.json']], myinput=[['data/book_clinical_cases/JMD-Cases-of-Interest.pdf', 'data/tmp_files/pages_selection.txt']], myoutput=[['data/outputs/vignettes_selection1.json']])
       
    #extract inputs into variables
    book_pdf = args.myinput[0][0]
    file_selected_pages = args.myinput[0][1] 
    target_file = args.myoutput[0][0]
    error_file = args.errors[0][0]
    
    
    
    #preprocess inputs
    book_individual_pages = parse_pdf_content(book_pdf)
    
    with open(file_selected_pages, "r") as f:
        list_pages_to_read_ = f.readlines() 
    list_pages_to_read = [int(item) for item in list_pages_to_read_]
    
    #apply processing
    dict_results = extract_selected_cases(book_individual_pages, list_pages_to_read)
    
    #dump outputs to json files
    with open(target_file, "w") as fo:
        json.dump(dict_results["vignettes"], fo)

    with open(error_file, "w") as fe:
        json.dump(dict_results["errors"], fe)
    
    

if __name__ == '__main__':
    main()