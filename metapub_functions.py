import os
from dotenv import load_dotenv
import pandas as pd
import requests

from metapub import PubMedFetcher, FindIt, convert 
from file_manipulations import read_input_file

async def initialize_metapub(ncbi_api_key):
    global fetch
    if ncbi_api_key == None:
        load_dotenv() #load API key from .env file
        ncbi_api_key = os.getenv('NCBI_API_KEY')
    fetch = PubMedFetcher() # Initialize the metapub fetcher


async def fetch_abstracts(ncbi_api_key, input_path): 
    await initialize_metapub(ncbi_api_key)
    pubmed_df= read_input_file(input_path)
    pubmed_df['Abstract'] = None
    pubmed_df['Relevant'] = None

    if len(pubmed_df['PMID'])>0:
        for index, pmid in enumerate(pubmed_df["PMID"]):
            pubmed_df.loc[index, "Abstract"] = fetch.article_by_pmid(pmid).abstract
    else:
        for idx, doi in enumerate(pubmed_df["DOI"]):
            if doi and len(doi)>0:
                try:
                    pubmed_df.loc[idx, "Abstract"] = fetch.article_by_doi(doi).abstract
                except Exception as e:
                    if "No PMID available for doi" in str(e):
                        print(e)
    return pubmed_df

async def download_free_pdfs(ncbi_api_key, input_path, download_folder_name):
    await initialize_metapub(ncbi_api_key)

    #Read in the list of articles to download if free
    pubmed_df= read_input_file(input_path)

    # Create the output folder
    os.makedirs(f"./outputs/{download_folder_name}", exist_ok=True) 

    # Download all pdfs that were scored as relevant
    query_parameters = {"downloadformat": "pdf"}
    max_title_len = 4

    missing_pdfs = pd.DataFrame(columns=pubmed_df.columns)

    for idx, doi in enumerate(pubmed_df["DOI"]):
        if len(doi)>0 and doi != "nan":
            try:
                pmid = convert.doi2pmid(doi)
                src = FindIt(pmid)
            except Exception as e:
                if "No PMID available for doi" in str(e):
                    print(e)

            if src.url:
                download_is_incomplete = True
                attempted_downloads_count = 0
                while (download_is_incomplete and attempted_downloads_count<5):
                    response = requests.get(src.url, params=query_parameters)

                    first_author = pubmed_df.loc[idx, "Authors"].split(",")[0]
                    year = pubmed_df.loc[idx, "Publication Year"]
                    title = ""
                    if len(pubmed_df.loc[idx, "Title"]) < max_title_len:
                        file_title_len = len(pubmed_df.loc[idx, "Title"])
                    else:
                        file_title_len = max_title_len
                    
                    for k in range(file_title_len):
                        if (k< file_title_len-1):
                            title = title + pubmed_df.loc[idx, "Title"].split(" ")[k] + " "
                        else:
                            title = title + pubmed_df.loc[idx, "Title"].split(" ")[k]

                    file_name = first_author + " - " + str(year) + " - " + title
                    with open(f"./outputs/{download_folder_name}/{file_name}.pdf", mode="wb") as file:
                        file.write(response.content)

                    attempted_downloads_count = attempted_downloads_count +1 

                    #check if PDF download is corrupted
                    try:
                        downloaded_pdf = f"./outputs/{download_folder_name}/{file_name}.pdf"
                        pdf_content = downloaded_pdf.read_bytes()
                        download_is_incomplete = False
                    except: 
                        break
            else:
                # if no URL, reason is one of "PAYWALL", "TXERROR", or "NOFORMAT"
                missing_pdfs.loc[len(missing_pdfs)] = pubmed_df.iloc[idx]
        else:
            # if no URL, reason is one of "PAYWALL", "TXERROR", or "NOFORMAT"
            missing_pdfs.loc[len(missing_pdfs)] = pubmed_df.iloc[idx]

    missing_pdfs.to_excel(f'./outputs/{download_folder_name}/missing_pdfs.xlsx')
