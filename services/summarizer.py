from utils.llm_call import llm_call
from prompts import you_tube_summary_prompt

def get_yt_summary(yt_transcript,level):
    prompt = you_tube_summary_prompt.format(level=level,transcript=yt_transcript)
    summary = llm_call(prompt)
    return summary

def get_pdf_summary(content):
    summary = llm_call(f"Summarize this content : {content}")
    return summary
