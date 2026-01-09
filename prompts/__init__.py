you_tube_summary_prompt = """Summarize the following transcript at a **{level}** level.
    Requirements:
    - Match the requested level (e.g., concise, detailed, explanatory).
    - Preserve key ideas and intent.
    - Avoid unnecessary repetition or filler.
    - Do not add information not present in the transcript.
    
    Transcript:
    {transcript}
    """

QA_prompt= """Based on the following PDF content, please answer the question accurately and concisely.
        PDF Content:
        {content}

        Question: {question}
        
        Answer:"""