import os
from datetime import datetime, timedelta
import time
import pandas as pd
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from typing import List
from google import genai
from google.genai import types
import pathlib
import json


from file_manipulations import read_input_file

##################################################
# Choose the LLM you want to use                 #
# (prompts have been tuned for Gemini 2.5 Flash) #
##################################################
llm_model = "gemini-2.5-flash" #preferred
# llm_model = "gemini-2.5-flash-lite"
rate_per_minute = 10

async def initialize_check_rate():
    global numb_calls_this_min
    global first_call_time
    original_time = datetime.now()
    numb_calls_this_min = 0
    first_call_time = datetime.now()

def check_rate():
    global numb_calls_this_min
    global first_call_time
    # if numb_calls_this_min == 0:
    #     first_call_time = datetime.now()

    last_call_time = datetime.now()
    time_diff = last_call_time - first_call_time
    # print(f"number_call_this_min: {numb_calls_this_min}; time_diff: {time_diff}")
    if time_diff.total_seconds() < 60: # if we are still within a minute, then we will check if we need to wait before calling the LLM again
        if numb_calls_this_min == rate_per_minute - 1: #if we have reached the max Rate Per Minute, we must figure out how long to wait before calling the LLM again
            wait_time = timedelta(minutes=1) - time_diff
            time.sleep(wait_time.total_seconds() + 5)
            numb_calls_this_min = 1
            first_call_time = datetime.now()
        else:
            numb_calls_this_min = numb_calls_this_min + 1
    else: #a minute has already passed, so we can call the LLM without issue
        numb_calls_this_min = 1
        first_call_time = datetime.now()


####################################################################################
# LLM Content                                                                      #
####################################################################################
async def initialize_llm(usr_provided_gemini_api_key):
    global client
    if len(usr_provided_gemini_api_key)>0:
        GOOGLE_API_KEY = usr_provided_gemini_api_key
    else:
        load_dotenv() 
        GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

    client = genai.Client(api_key=GOOGLE_API_KEY)

    #check API Key Validity before proceeding
    test_question = "reply with hello"
    try:
        check_rate()
        test = client.models.generate_content(
                model=llm_model,
                contents=[
                    test_question
                ],
            )
    except:
        load_dotenv() 
        GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
        client = genai.Client(api_key=GOOGLE_API_KEY)

##################################
# Logic for Relevance Evaluation #
class GradeDocuments(BaseModel):
    """Binary score for relevance check on retrieved articles."""
    binary_score: str = Field(
        description="Articles remain a part of the search criteria, 'yes' or 'no'"
    )

async def grade_article_abstracts(pubmed_df, search_keywords, exclusion_criteria):
    tab_1_error = None

    sel_model = ChatGoogleGenerativeAI(
        model=llm_model,
        temperature=0,
        max_tokens=None,
        timeout=None,
        max_retries=2,
    )

    # LLM with function call
    structured_llm_grader = sel_model.with_structured_output(GradeDocuments) 
    system_prompt = """
        <INSTRUCTIONS>
        You are a grader assessing relevance of an article's abstract to a subject. \n 
        If the abstract contains keyword(s) or semantic meaning related to the subject, grade it as relevant. \n
        If the abstract contains any of the exclusion criteria listed below, then grade it as irrelevant \n
        Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question.
        </INSTRUCTIONS>
        
        """
    human_prompt = """ 
        <ABSTRACT>
        {abstract}
        </ABSTRACT>

        <SUBJECT>
        {subject}
        </SUBJECT>

        <EXCLUSION CRITERIA>
        {exclusion_criteria}
        </EXCLUSION CRITERIA>
        """

    grade_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", human_prompt),
        ]
    )

    abstract_grader = grade_prompt | structured_llm_grader   

    #following lines test the grader
    subject = search_keywords
    exclusion_criteria = f"Exclude any articles that fulfill the following criteria: {exclusion_criteria}"

    # step_increments = 0.5/len(pubmed_df['Abstract'])

    for index, abstract in enumerate(pubmed_df["Abstract"]):
        # abstract = pubmed_df.loc[0, "Abstract"]
        print(f"evaluating article {index} of {str(len(pubmed_df["Abstract"]))}")
        abstract_is_graded = False
        while (abstract_is_graded == False):
            check_rate()
            try:
                score = abstract_grader.invoke({"subject": subject, "abstract": abstract, "exclusion_criteria": exclusion_criteria})
                pubmed_df.loc[index,"Relevant"] = score.binary_score
                # progress_bar.set((index+1)*step_increments)
                abstract_is_graded = True
            except Exception as e:
                tab_1_error = str(e)
                print("tab_1_error", tab_1_error)
                print("score", score)
                if "retry_delay" in tab_1_error:
                    print("waiting for end of minute to resume prompting Gemini...")
                    time.sleep(1000)
                    tab_1_error = None
                else:
                    break
            
    return pubmed_df, tab_1_error

async def remove_irrelevant_articles(pubmed_df, download_folder_name):
    # Get rid of all articles in the dataframe marked as irrelevant
    pubmed_df = pubmed_df[pubmed_df["Relevant"] == "yes"]
    pubmed_df = pubmed_df.drop(columns="Relevant")
    pubmed_df.reset_index(inplace=True, drop=True)
    pubmed_df.to_excel(f'./outputs/{download_folder_name}/filtered_in_only_relevant_articles.xlsx')

    
########################################
# Logic for Literature Review Analysis #
def get_all_file_paths(directory_path):
    """
    Collects the absolute paths of all files within a given directory
    and its subdirectories.

    Args:
        directory_path (str): The path to the directory to traverse.

    Returns:
        list: A list containing the absolute paths of all found files.
    """
    file_paths = []
    for root, _, files in os.walk(directory_path):
        for file in files:
            full_path = os.path.join(root, file)
            file_paths.append(os.path.abspath(full_path))
    return file_paths

class Technology_Manuf(BaseModel):
    """
    Represents all technology and associated manufacturers listed in the article
    """
    technology: str
    manufacturer: str

class Technology_Manuf_Combo(BaseModel):
    """ 
    Represents a List of paired technology and manufaturers
    """
    tech_manuf: List[Technology_Manuf]

class Sample_Size_Reasoning(BaseModel):
    """ 
    Counts the number of robotically-assisted vs. conventional cases that were examined in the article
    Also provides reasoning that the LLM used to come to these conclusions.
    """
    conv_sample_size: int
    robotic_sample_size: int
    reasoning: str
   
class Harm_Details(BaseModel):
    """
    Represents a single harm and its occurrence count.
    """
    harm_name: str
    occurrence_count: int

class Harms_Count_Confidence(BaseModel):
    """
    Represents all harms-occurences for the article
    """
    harms: List[Harm_Details]
    confidence_score: int

system_ins=["You're a meticulous researcher.",
            "Your mission is to analyze the provided documents and provide accurate answers to requests.",
            "If you do not know the answer to the question, say that you do not know.",
            "Remove all special font formatting from your answer."]

system_ins_harms=["Your mission is to analyze the provided documents and provide accurate answers to requests.",
                  "If you do not know the answer to the question, say that you do not know.",
                  "Provide a confidence score as a percentage to indicate how accurate your answer is to the request."]


async def populate_literature_review_summary_dataframe(focus, input_path, pdf_folder):
    pubmed_df = read_input_file(input_path)
    all_pdfs = get_all_file_paths(pdf_folder)

    error = None
    lit_rev_df = pd.DataFrame(columns=["Title", "Authors", "Year", "Technology Used", "Manufacturer", 
                                       "Study Type", "Objectives", "Conclusions", "Sample Size", "LLM's Reasoning on Sample Size",
                                       "Harms", "LLM's Confidence in Accuracy of Returned Harms"])

    for i in range(len(pubmed_df)):
        print(f"processing article {i+1} of {len(pubmed_df)} of the lit_rev_summary table...")
        ############################################
        # Create the Annex A Table for the Article #
        ############################################
        # read Title from csv
        title = pubmed_df.loc[i, "Title"]

        # read Author from csv
        authors = pubmed_df.loc[i, "Authors"]

        # read Year from csv
        year = pubmed_df.loc[i, "Publication Year"]

        # Retrieve and encode the PDF byte
        first_author = authors.split(",")[0]

        #find the path to the corresponding pdf 
        filepath = None
        for j in range(len(all_pdfs)):
            if first_author in all_pdfs[j] and str(year) in all_pdfs[j]:
                filepath = pathlib.Path(all_pdfs[j])
        if filepath == None:
            row = pd.DataFrame(data = {"Title": title, 
                                        "Authors": authors, 
                                        "Year": year, 
                                        "Technology Used": "N/A. Could not analyze; Missing PDF.", 
                                        "Manufacturer": "N/A. Could not analyze; Missing PDF.", 
                                        "Study Type": "N/A. Could not analyze; Missing PDF.", 
                                        "Objectives": "N/A. Could not analyze; Missing PDF.", 
                                        "Conclusions": "N/A. Could not analyze; Missing PDF.", 
                                        "Sample Size": "N/A. Could not analyze; Missing PDF.", 
                                        "LLM's Reasoning on Sample Size": "N/A. Could not analyze; Missing PDF.",
                                        "Harms": "N/A. Could not analyze; Missing PDF.",
                                        "LLM's Confidence in Accuracy of Returned Harms": "N/A. Could not analyze; Missing PDF."
                                        },
                                index = [i])
        
        else:
            #check if PDF is corrupted
            try:
                file_content = filepath.read_bytes()
            except: 
                break

            # Manufacturer & Tech from LLM 
            print("finding manufacturer")
            question = "Identify the manufacturers of the technologies listed"
            check_rate()
            try:
                manufacturer_tech = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(data=file_content, mime_type='application/pdf'),
                        question
                    ],
                    config = types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=Technology_Manuf_Combo.model_json_schema(),
                        system_instruction = system_ins
                    )
                )
            except Exception as e:
                if "has no pages" in str(e):
                    row = pd.DataFrame(data = {"Title": title, 
                                        "Authors": authors, 
                                        "Year": year, 
                                        "Technology Used": "Could not analyze because PDF is corrupted", 
                                        "Manufacturer": "Could not analyze because PDF is corrupted", 
                                        "Study Type": "Could not analyze because PDF is corrupted", 
                                        "Objectives": "Could not analyze because PDF is corrupted", 
                                        "Conclusions": "Could not analyze because PDF is corrupted", 
                                        "Sample Size": "Could not analyze because PDF is corrupted", 
                                        "LLM's Reasoning on Sample Size": "Could not analyze because PDF is corrupted",
                                        "Harms": "Could not analyze because PDF is corrupted",
                                        "LLM's Confidence in Accuracy of Returned Harms": "Could not analyze because PDF is corrupted"
                                        },
                                index = [i])

                    lit_rev_df = pd.concat([lit_rev_df, row], ignore_index=True)
                    continue
                else:
                    break
            
            try:
                final_manuf_tech = json.loads(manufacturer_tech.text)
                tech_text = ""
                manufacturer_text = ""
                for k in range(len(final_manuf_tech["tech_manuf"])):
                    tech_text = tech_text + str(k+1) + ". " + final_manuf_tech["tech_manuf"][k]["technology"] + "\n"
                    manufacturer_text = manufacturer_text + str(k+1) + ". " + final_manuf_tech["tech_manuf"][k]["manufacturer"] + "\n"
            except Exception as e:
                tech_text = f"Error: Could not decode '{str(manufacturer_tech.text)}'"
                manufacturer_text = f"Error: Could not decode '{str(manufacturer_tech.text)}'"


            # Study Type from LLM (check if you can export this directly from Pubmed somehow.....)
            print("finding study type")
            question = "Identify the type of study that was performed by the article. If the study type is unclear, return 'Study Type Unknown'."
            check_rate()
            try:
                study_type = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(
                            data=file_content, 
                            mime_type='application/pdf'
                        ),
                        question
                    ],
                    config = types.GenerateContentConfig(
                        system_instruction = system_ins
                    )
                )
            except Exception as e:
                error = str(e)
                break

            # Objective of the Article from LLM
            print("finding objective")
            question = "Provide a brief summary of the objective(s) of the article"
            check_rate()
            try:
                objective = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(
                            data=file_content,
                            mime_type='application/pdf',
                        ),
                        question
                    ],
                    config = types.GenerateContentConfig(
                        system_instruction = system_ins
                    )
                )
            except Exception as e:
                error = str(e)
                break

            # Conclusion from LLM 
            print("finding conclusion")
            question = "Provide a brief summary of the conclusion(s) of the article"
            check_rate()
            try:
                conclusion = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(
                            data=file_content,
                            mime_type='application/pdf',
                        ),
                        question
                    ],
                    config = types.GenerateContentConfig(
                        system_instruction = system_ins
                    )
                )
            except Exception as e:
                error = str(e)
                break

            # Patient Sample size from LLM
            print("finding sample size")
            question = f"Find the number of adult patients that underwent conventional surgery compared to {focus}"
            check_rate()
            try:
                sample_size = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(
                            data=file_content,
                            mime_type='application/pdf',
                        ),
                        question
                    ],
                    config = types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=Sample_Size_Reasoning.model_json_schema(),
                        system_instruction = system_ins
                    )
                )
            except Exception as e:
                error = str(e)
                break

            try:
                final_sample = json.loads(sample_size.text)
                sample_size_text = f"conventional: {str(final_sample['conv_sample_size'])} \n" + f"{focus}: {str(final_sample["robotic_sample_size"])} \n" 
                sample_reasoning_text = final_sample["reasoning"]
            except Exception as e:
                sample_size_text = f"Error: Could not decode '{str(sample_size.text)}'"
                sample_reasoning_text = ""

            # Hazards and Harms from LLM 
            print("finding hazards and harms")
            step_by_step_prompt = f"""
            Let's go through this step by step. 
            First, list the number of observed hazards, harms, adverse events, and complications. 
            Second, remove any that occurred due to elements unrelated to the {focus}. 
            Third, if no more entries exist, then return ['No specific hazards, harms, adverse events, or complications were reported', 0]. Otherwise, count the number of occurrence of each entry. 
            """
            check_rate()
            try:
                harms = client.models.generate_content(
                    model=llm_model,
                    contents=[
                        types.Part.from_bytes(
                            data=file_content,
                            mime_type='application/pdf',
                        ),
                        step_by_step_prompt
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type='application/json',
                        response_schema=Harms_Count_Confidence.model_json_schema(),
                        system_instruction = system_ins_harms
                    ),
                )
            except Exception as e:
                error = str(e)
                break
            
            try:
                final_harms = json.loads(harms.text)
                harm_text = ""
                for k in range(len(final_harms["harms"])):
                    if "No specific hazards" not in final_harms["harms"][k]["harm_name"]:
                        harm_text = harm_text + final_harms["harms"][k]["harm_name"] + ": " + str(final_harms["harms"][k]["occurrence_count"]) + "\n"

                if len(harm_text) == 0:
                    harm_text = "No specific hazards, adverse events, or complications were reported"
            except Exception as e:
                harm_text = f"Error: Could not decode '{str(harms.text)}'"
                    
            harms_conf_score = "The LLM is " + str(final_harms["confidence_score"]) + f"% sure of its answer."

            row = pd.DataFrame(data = {"Title": title, 
                                        "Authors": authors, 
                                        "Year": year, 
                                        "Technology Used": tech_text, 
                                        "Manufacturer": manufacturer_text, 
                                        "Study Type": study_type.text, 
                                        "Objectives": objective.text, 
                                        "Conclusions": conclusion.text, 
                                        "Sample Size": sample_size_text, 
                                        "LLM's Reasoning on Sample Size": sample_reasoning_text,
                                        "Harms": harm_text,
                                        "LLM's Confidence in Accuracy of Returned Harms": harms_conf_score
                                        },
                                index = [i])

        lit_rev_df = pd.concat([lit_rev_df, row], ignore_index=True)

    return lit_rev_df, error

def get_unanalyzed_article_list(input_path, analyzed_articles_list_length):
    pubmed_df = read_input_file(input_path)

    start_index = int(analyzed_articles_list_length)-1
    print("start_index", start_index)
    unanalyzed_df = pubmed_df.loc[start_index:]

    return unanalyzed_df