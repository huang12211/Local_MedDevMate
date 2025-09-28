import os
import customtkinter
import re
import webbrowser
import asyncio
import tk_async_execute as tae
import datetime

from tkinter import filedialog
from llm_functions import initialize_check_rate, check_rate, initialize_llm, grade_article_abstracts, remove_irrelevant_articles, populate_literature_review_summary_dataframe, get_unanalyzed_article_list
from metapub_functions import fetch_abstracts, download_free_pdfs

######################
# CALLBACK FUNCTIONS #
###################### 
async def filter_out_irrelevant_articles_callback():
    global input_path
    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 0:
            tab.configure(state="disabled")

    tab1_pubmed_api_key_field.configure(state="disabled", text_color="gray")
    pub_api_key = tab1_pubmed_api_key_field.get()

    tab1_google_api_key_field.configure(state="disabled", text_color="gray")
    google_api_key = tab1_google_api_key_field.get()

    tab1_input_path_field.configure(state="disabled", text_color="gray")
    tab1_input_path_field_button.configure(state="disabled")

    tab1_output_folder_name_field.configure(state="disabled", text_color="gray")
    output_folder_name = tab1_output_folder_name_field.get()
    
    tab1_search_keywords_field.configure(state="disabled", text_color="gray")
    search_keywords = tab1_search_keywords_field.get()
    
    tab1_exclusion_criteria_textbox.configure(state="disabled", text_color="gray")
    exclusion_criteria = tab1_exclusion_criteria_textbox.get("1.0", "end")

    tab1_submit.configure(state="disabled")
    
    tab1_progressbar.grid(row=11, column=0, padx=20, pady=(0, 20), columnspan=2) #show progress bar
    tab1_progressbar.start()
    tab1_progress_description.grid(row=12, column=0, padx=20, pady=(0, 20), columnspan=2) 

    # print("all variables: ", pub_api_key, output_folder_name, search_keywords, exclusion_criteria)
    print("fetching abstracts...")
    # await asyncio.sleep(1)
    pubmed_df = await fetch_abstracts(pub_api_key, input_path)

    await initialize_check_rate()
    print("checkrate initialized")
    check_rate()
    await initialize_llm(google_api_key)
    print("llm initialized")

    tab1_progress_description.configure(text="Evaluating relevance of articles...")
    print("Evaluating article abstracts...")

    os.makedirs(f"./outputs/{output_folder_name}", exist_ok=True)
    evaluated_df, tab_1_error = await grade_article_abstracts(pubmed_df, search_keywords, exclusion_criteria)
    if tab_1_error == None:
        pubmed_df.to_excel(f'./outputs/{output_folder_name}/graded_article_abstracts.xlsx')
        await remove_irrelevant_articles(evaluated_df, output_folder_name)
        print("filtered out all irrelevant articles")
        tab1_progressbar.stop()
        tab1_progressbar.grid_forget()
        tab1_progress_description.configure(text="Success! \n If you wish to inspect how the LLM classified each article, refer 'graded_article_abstracts.xlsx'. 'filtered_in_only_relevant_articles.xlsx' contains only the articles that were considered to be relevant by the LLM.")
    else: 
        tab1_progressbar.stop()
        tab1_progressbar.grid_forget()
        tab1_progress_description.configure(text="Failed! \n Gemini LLM Daily Quota Has been used up.")
        
    #Re-enable the other tabs
    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 0:
            tab.configure(state="normal")

def filter_out_irrelevant_articles_submit_btn_clicked():
    tae.async_execute(filter_out_irrelevant_articles_callback(), wait=True, visible=False, pop_up=False, callback=None, master=tab_1)


async def download_free_pdfs_callback():
    global input_path

    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 1:
            tab.configure(state="disabled")
    
    api_key = tab2_pubmed_api_key_field.get()
    tab2_pubmed_api_key_field.configure(state="disabled", text_color="gray")

    tab2_input_path_field.configure(state="disabled", text_color="gray")
    tab2_input_path_field_button.configure(state="disabled")

    # chosen_database = database_used_field.get()
    # database_used_field.configure(state="disabled")

    output_folder_name = output_folder_name_field.get()
    output_folder_name_field.configure(state="disabled", text_color="gray")

    tab2_submit.configure(state="disabled")
    
    tab2_progressbar.grid(row=11, column=0, padx=20, pady=(0, 20), columnspan=2) #show progress bar
    tab2_progressbar.start()
    tab2_progress_description.grid(row=12, column=0, padx=20, pady=(0, 20), columnspan=2) 

    await download_free_pdfs(api_key, input_path, output_folder_name)

    tab2_progressbar.stop()
    tab2_progressbar.grid_forget()
    tab2_progress_description.configure(text="Success! \n All Free Access PDFs have been downloaded to your output folder.")

    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 1:
            tab.configure(state="normal")

def download_free_pdfs_btn_clicked():
    tae.async_execute(download_free_pdfs_callback(), wait=True, visible=False, pop_up=False, callback=None, master=tab_2)

async def launch_lit_rev_callback():
    global input_path, folder_path

    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 1:
            tab.configure(state="disabled")
    
    tab3_google_api_key_field.configure(state="disabled", text_color="gray")
    google_api_key = tab3_google_api_key_field.get()

    focus_field.configure(state="disabled", text_color="gray")
    focus = focus_field.get()

    tab3_input_path_field.configure(state="disabled", text_color="gray")
    tab3_input_path_field_button.configure(state="disabled")
    pdf_folder_name_field.configure(state="disabled", text_color="gray")
    pdf_folder_button.configure(state="disabled")

    tab3_submit.configure(state="disabled")
    
    tab3_progressbar.grid(row=11, column=0, padx=20, pady=(0, 20), columnspan=2) #show progress bar
    tab3_progressbar.start()
    tab3_progress_description.grid(row=12, column=0, padx=20, pady=(0, 20), columnspan=2) 


    # await asyncio.sleep(5)
    # error = "error occurred"
    await initialize_check_rate()
    print("checkrate initialized")
    check_rate()
    await initialize_llm(google_api_key)
    print("llm initialized")
    analyzed_df, error = await populate_literature_review_summary_dataframe(focus, input_path, folder_path)

    tab3_progressbar.stop()
    tab3_progressbar.grid_forget()

    logtime = datetime.datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    if error == None:
        analyzed_df.to_excel(f'{folder_path}/{logtime}_literature_review_summary_COMPLETED.xlsx')
        tab3_progress_description.configure(text="Success! \n The literature_review_summary.xlsx has been added to your PDFs folder.")
    else: 
        analyzed_df.to_excel(f'{folder_path}/{logtime}_literature_review_summary_partial.xlsx')
        unanalyzed_df = get_unanalyzed_article_list(input_path, len(analyzed_df))
        unanalyzed_df.to_excel(f'{folder_path}/{logtime}_unanalyzed_list_of_articles.xlsx')
        tab3_progress_description.configure(text=f"Analysis FAILED! \n Error: {error}. \n Articles that could not be analyzed are listed in unanalyzed_list_of_articles.xlsx")
    
    for indx, tab in enumerate(tabview._segmented_button._buttons_dict.values()):
        if indx != 1:
            tab.configure(state="normal")

def launch_lit_rev_btn_clicked():
    tae.async_execute(launch_lit_rev_callback(), wait=True, visible=False, pop_up=False, callback=None, master=tab_3)

##################
#    FRONTEND    #
################## 
def open_website():
    webbrowser.open_new("https://ncbiinsights.ncbi.nlm.nih.gov/2017/11/02/new-api-keys-for-the-e-utilities/")

def select_file(input_path_field):
    global input_path
    input_path = filedialog.askopenfilename(
        title="Select a file",
        filetypes=[("All files", "*.*")]
    )
    if input_path:
        print(f"Selected file: {input_path}")
        file_path_abr = re.search(r"[^/]*$", input_path)
        input_path_field.configure(state="normal")
        input_path_field.delete(0, customtkinter.END)
        input_path_field.insert(0, file_path_abr.group())
        input_path_field.configure(state="disabled")

def select_folder(folder_path_field):
    global folder_path
    folder_path = filedialog.askdirectory(
        title="Select a folder"
    )
    if folder_path:
        print(f"Selected folder: {folder_path}")
        folder_path_abr = re.search(r"[^/]*$", folder_path)
        folder_path_field.configure(state="normal")
        folder_path_field.delete(0, customtkinter.END)
        folder_path_field.insert(0, folder_path_abr.group())
        folder_path_field.configure(state="disabled")

app = customtkinter.CTk()
app.title("Product Characterization - Literature Review Agent")
app.geometry("800x800")
app.grid_columnconfigure(0, weight=1)

tabview = customtkinter.CTkTabview(master=app)
tabview.grid(row=0, column=0, padx=20, pady=0, sticky="ew")
tab_1 = tabview.add("Remove Irelevant Articles")  # add tab at the end
tab_2 = tabview.add("Fetch all Free PDFs")  # add tab at the end
tab_3 = tabview.add("Analyze all Collected PDFs")  # add tab at the end
for button in tabview._segmented_button._buttons_dict.values():
    button.configure(width=100, height=50)
tabview.set("Remove Irelevant Articles")  # set currently visible tab

#######################################
# Filter Irrelevant Articles Tab View #
tab_1.grid_columnconfigure((0, 1), weight=1)

pubmed_api_key_label = customtkinter.CTkLabel(tab_1, text="Pubmed API Key:", fg_color="transparent")
pubmed_api_key_label.grid(row=1, column=0, padx=20, pady=(20, 0), sticky="se")
tab1_pubmed_api_key_field = customtkinter.CTkEntry(tab_1, placeholder_text="Leave blank if you've entered your key into the .env file")
tab1_pubmed_api_key_field.grid(row=1, column=1, padx=20, pady=0, sticky="sew")
pubmed_api_key_instruction = customtkinter.CTkLabel(tab_1, 
                                                    text="You need an NCBI API key which you can get HERE", 
                                                    text_color="blue", 
                                                    cursor="hand2",
                                                    wraplength=380)
pubmed_api_key_instruction.bind("<Button-1>", lambda e: open_website())
pubmed_api_key_instruction.grid(row=2, column=1, padx=0, pady=(0, 20), sticky="new")

google_api_key_label = customtkinter.CTkLabel(tab_1, text="Gemini API Key:", fg_color="transparent")
google_api_key_label.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="se")
tab1_google_api_key_field = customtkinter.CTkEntry(tab_1, placeholder_text="Leave blank if you've entered your key into the .env file")
tab1_google_api_key_field.grid(row=3, column=1, padx=20, pady=(0, 20), sticky="sew")

input_path_label = customtkinter.CTkLabel(tab_1, text="Pubmed or Embase export:", fg_color="transparent")
input_path_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="se")
tab1_input_path_field = customtkinter.CTkEntry(tab_1, placeholder_text="No file selected.")
tab1_input_path_field.grid(row=4, column=1, padx=20, pady=(0, 0), sticky="sew")
tab1_input_path_field.configure(state="disabled")
tab1_input_path_field_button = customtkinter.CTkButton(tab_1, text="Select File", command=lambda: select_file(tab1_input_path_field))
tab1_input_path_field_button.grid(row=5, column=1, padx=20, pady=(0, 20),)

output_folder_name_label = customtkinter.CTkLabel(tab_1, text="Name of output folder:", fg_color="transparent")
output_folder_name_label.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="e")
tab1_output_folder_name_field = customtkinter.CTkEntry(tab_1, placeholder_text="DD-MMM-YYYY - Pubmed/Embase - Search 1")
tab1_output_folder_name_field.grid(row=6, column=1, padx=20, pady=(0, 20), sticky="ew")

search_keywords_label = customtkinter.CTkLabel(tab_1, text="Search Keywords:", fg_color="transparent")
search_keywords_label.grid(row=7, column=0, padx=20, pady=(0, 20), sticky="e")
tab1_search_keywords_field = customtkinter.CTkEntry(tab_1, placeholder_text="Example: (shoudler arthroplast* or shoulder replacem*) and navig*")
tab1_search_keywords_field.grid(row=7, column=1, padx=20, pady=(0, 20), sticky="ew")

exclusion_criteria_label = customtkinter.CTkLabel(tab_1, text="Exclusion criteria:", fg_color="transparent")
exclusion_criteria_label.grid(row=8, column=0, padx=20, pady=(0, 20), sticky="e")
tab1_exclusion_criteria_textbox = customtkinter.CTkTextbox(tab_1)
tab1_exclusion_criteria_textbox.grid(row=8, column=1, padx=20, pady=(0, 20), sticky="ew")

tab1_submit = customtkinter.CTkButton(tab_1, text="Submit", command=filter_out_irrelevant_articles_submit_btn_clicked)
tab1_submit.grid(row=9, column=0, padx=20, pady=(0, 20), columnspan=2)

tab1_progressbar = customtkinter.CTkProgressBar(tab_1, orientation="horizontal", width=300)
tab1_progressbar.set(0)

tab1_progress_description = customtkinter.CTkLabel(tab_1, 
                                                   text="Fetching Abstracts for all Articles...", 
                                                   fg_color="transparent",
                                                   wraplength=700)


######################################
# Fetch Articles using DOIs Tab View #
tab_2.grid_columnconfigure((0, 1), weight=1)
explanation_label = customtkinter.CTkLabel(tab_2,
                                           font = customtkinter.CTkFont(family="Arial", size=14, weight="bold"),
                                           justify = "left",
                                           text="All PDFs with Free Access will be downloaded to the specified output folder. You will also find an excel sheet named 'missing_pdfs' listing the PDFs in the input file that could not be downloaded.", 
                                           fg_color="transparent",
                                           wraplength=700)
explanation_label.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew", columnspan=2)

pubmed_api_key_label = customtkinter.CTkLabel(tab_2, text="Pubmed API Key:", fg_color="transparent")
pubmed_api_key_label.grid(row=2, column=0, padx=20, pady=(20, 0), sticky="se")
tab2_pubmed_api_key_field = customtkinter.CTkEntry(tab_2, 
                                                   placeholder_text="Leave blank if you've entered your key into the .env file",
                                                   width=350)
tab2_pubmed_api_key_field.grid(row=2, column=1, padx=20, pady=0, sticky="sew")
pubmed_api_key_instruction = customtkinter.CTkLabel(tab_2, 
                                                    text="You need an NCBI API key which you can get HERE", 
                                                    text_color="blue", 
                                                    cursor="hand2",
                                                    wraplength=380)
pubmed_api_key_instruction.bind("<Button-1>", lambda e: open_website())
pubmed_api_key_instruction.grid(row=3, column=1, padx=0, pady=(0, 20), sticky="new")

tab2_input_path_label = customtkinter.CTkLabel(tab_2, 
                                               text="Input .csv or .xlsx file \n (containing a column named 'DOI'):", 
                                               fg_color="transparent",
                                               wraplength=300)
tab2_input_path_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="se")
tab2_input_path_field = customtkinter.CTkEntry(tab_2, placeholder_text="No file selected.")
tab2_input_path_field.grid(row=4, column=1, padx=20, pady=(0, 0), sticky="sew")
tab2_input_path_field.configure(state="disabled")
tab2_input_path_field_button = customtkinter.CTkButton(tab_2, text="Select File", command=lambda: select_file(tab2_input_path_field))
tab2_input_path_field_button.grid(row=5, column=1, padx=20, pady=(0, 20),)

# database_used_label = customtkinter.CTkLabel(tab_2, text="Pubmed or Embase:", fg_color="transparent")
# database_used_label.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="e")
# database_used_field = customtkinter.CTkComboBox(tab_2, values=["PubMed", "Embase"])
# database_used_field.set("PubMed")
# database_used_field.grid(row=5, column=1, padx=20, pady=(0, 20), sticky="ew")

output_folder_name_label = customtkinter.CTkLabel(tab_2, text="Name of output folder:", fg_color="transparent")
output_folder_name_label.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="e")
output_folder_name_field = customtkinter.CTkEntry(tab_2, placeholder_text="DD-MMM-YYYY - Pubmed/Embase - Search 1")
output_folder_name_field.grid(row=6, column=1, padx=20, pady=(0, 20), sticky="ew")

tab2_submit = customtkinter.CTkButton(tab_2, text="Start Download", command=download_free_pdfs_btn_clicked)
tab2_submit.grid(row=10, column=0, padx=20, pady=(20, 20), columnspan=2)

tab2_progressbar = customtkinter.CTkProgressBar(tab_2, orientation="horizontal", width=300)
tab2_progressbar.set(0)

tab2_progress_description = customtkinter.CTkLabel(tab_2, 
                                                   text="Downloading all Articles in provided input file", 
                                                   fg_color="transparent",
                                                   wraplength=700)

###############################################
# Literature Review Summary Analysis Tab View #
tab_3.grid_columnconfigure((0, 1), weight=1)
explanation_label = customtkinter.CTkLabel(tab_3,
                                           font = customtkinter.CTkFont(family="Arial", size=12, weight="bold"),
                                           justify = "left",
                                           text="Once you provide the technolgy being evaluated against conventional surgery, input file listing the relevant articles, and the path to the folder containing all PDFs listed in the input file, this program provides a 'literature_review_summary.xlsx' in the PDFs folder including the following information for each article:\n"
                                           + "- Mentioned technology and associated manufacturer\n"
                                           + "- Study Type\n"
                                           + "- Objective\n"
                                           + "- Conclusion\n"
                                           + "- Sample Size of the conventional surgery group to the technology-focused group\n"
                                           + "- LLM's reasoning on how it determined the samples sizes of the technology-focused and conventional surgery groups*\n"
                                           + "- Hazards and Harms associated with the technology-focused group\n"
                                           + "- LLM's confidence in the accuracy of the list of hazards and harms it has listed*\n\n"
                                           + "*These columns are provided for Human evaluation and should deleted bfore attaching it to the final report.", 
                                           fg_color="transparent",
                                           wraplength=700)
explanation_label.grid(row=1, column=0, padx=20, pady=(10, 20), sticky="ew", columnspan=2)

google_api_key_label = customtkinter.CTkLabel(tab_3, text="Gemini API Key:", fg_color="transparent")
google_api_key_label.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="se")
tab3_google_api_key_field = customtkinter.CTkEntry(tab_3, 
                                                   placeholder_text="Leave blank if you've entered your key into the .env file",
                                                   width=350)
tab3_google_api_key_field.grid(row=2, column=1, padx=20, pady=(0, 20), sticky="sew")

focus_label = customtkinter.CTkLabel(tab_3, 
                                     text="Subject/Technology being evaluated: \n (Complete this sentence:\n Find harms of conventional surgery compared to _______________)", 
                                     fg_color="transparent",
                                     justify="right",
                                     wraplength=300)
focus_label.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="se")
focus_field = customtkinter.CTkEntry(tab_3, placeholder_text="Example: robotically-assisted surgery")
focus_field.grid(row=3, column=1, padx=20, pady=(0, 20), sticky="sew")

input_path_label = customtkinter.CTkLabel(tab_3, text="Input excel file listing articles to analyze:", fg_color="transparent")
input_path_label.grid(row=4, column=0, padx=20, pady=(10, 0), sticky="se")
tab3_input_path_field = customtkinter.CTkEntry(tab_3, placeholder_text="Each row must have the title, authors, and year.")
tab3_input_path_field.grid(row=4, column=1, padx=20, pady=(0, 0), sticky="sew")
tab3_input_path_field.configure(state="disabled")
tab3_input_path_field_button = customtkinter.CTkButton(tab_3, text="Select File", command=lambda: select_file(tab3_input_path_field))
tab3_input_path_field_button.grid(row=5, column=1, padx=20, pady=(0, 20))

pdf_folder_name_label = customtkinter.CTkLabel(tab_3, text="Folder containing PDFs to analyze", fg_color="transparent")
pdf_folder_name_label.grid(row=6, column=0, padx=20, pady=(0, 0), sticky="e")
pdf_folder_name_field = customtkinter.CTkEntry(tab_3, placeholder_text="No folder selected.")
pdf_folder_name_field.grid(row=6, column=1, padx=20, pady=(0, 0), sticky="ew")
pdf_folder_button = customtkinter.CTkButton(tab_3, text="Select Folder", command=lambda: select_folder(pdf_folder_name_field))
pdf_folder_button.grid(row=7, column=1, padx=20, pady=(0, 20))

tab3_submit = customtkinter.CTkButton(tab_3, text="Launch Analysis", command=launch_lit_rev_btn_clicked)
tab3_submit.grid(row=10, column=0, padx=6, pady=(20, 20), columnspan=2)

tab3_progressbar = customtkinter.CTkProgressBar(tab_3, orientation="horizontal", width=250)
tab3_progressbar.set(0)

tab3_progress_description = customtkinter.CTkLabel(tab_3, 
                                                   text="Analyzing Articles...", 
                                                   fg_color="transparent",
                                                   wraplength=700)

tae.start()
app.mainloop()
tae.stop()