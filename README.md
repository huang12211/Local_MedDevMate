# Product_Characterization_AI_Tools
## Overview:
Tired of performing Product Characterization Reports manually? Well look no further because here is a tool that you can use to automate much of this process! 

Tools that exist: 
- Literature Review AI Assistants

Tools that are under development:
- Maude Analysis AI Assistant

## Project status
This is a passion project and is developped during nights and weekends. 

## Literature Review AI Assistants:
### What can it do?
This tool contains 3 tabs which breaks up the typical Literature Review Process at specific checkpoints where human judgement is required before moving on. 
- Assistant 1: Given the raw search results from PubMed or Embase, this assistant analyzes all the abstracts against your inclusion/exclusion criteria and removes any irrelevant articles from the search results.
- Assistant 2: Given search results of relevant articles, this assistant fetches all of the articles with Free Access and downloads them for you.
- Assistant 3: Given the serch results of relevant articles and the folder containing all associated PDFs, this assistant analyzes the articles and extracts the information ZCAS typically uses to evaluate the literature including the isolation of all hazards, harms, and adverse events.

*Note: For elements requiring LLM reasoning that can cause it to hallucinate, the LLM's reasoning is also exposed to you as part of the output of the assistant so that you can review and judge for yourself if the LLM came to the correct conclusion. 

### How to Install:
To use this tool out of the box, just download the "product_characterization.exe" file from the "dist" folder and structure your files on your computer as illustrated below before running the .exe file.

```
project_folder
│   product_characterization.exe  
│
└───outputs   

```


### Technical Details:
The hard-coded prompts are tailored for Google's LLM: gemini-2.5-flash

Tools:
- Langchain
- Pydantic
- Metapub (for fetching articles & their metadata/abstracts)
- Custom Tkinter (UI)


