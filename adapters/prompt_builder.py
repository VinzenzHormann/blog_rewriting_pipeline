# Define Flag Bitmasks
FLAG_NO_CATEGORY        = 1   # 00000001
FLAG_NO_SUBHEADINGS     = 2   # 00000010
FLAG_STRIKING_DISTANCE  = 4   # 00000100
FLAG_NO_POSITION_TECHNICAL_ISSUE         = 8   # 00001000
FLAG_THIN_CONTENT       = 16  # 00010000
FLAG_CRAWLED_NOT_INDEXED= 32  # 00100000
FLAG_NO_POSITION_SUBM_AND_INDEXED = 64 #01000000 
FLAG_NO_TOP_KEYWORD = 128 #position 8 10000000 EMPTY

PROMPT_MODULES = {
    FLAG_NO_SUBHEADINGS: "- STRUCTURAL HEADING FIX: Divide the content logically using clear, descriptive <h2> and <h3> tags. Break up walls of text so the article is easily scannable by both readers and search engines.",
    FLAG_STRIKING_DISTANCE: "- RANKING PUSH (Striking Distance): This post ranks on page 2 (positions 8-20). Enhance keyword density naturally, add sub-sections answering common questions, and deepen the core analysis to push it onto page 1.",
    FLAG_NO_POSITION_SUBM_AND_INDEXED: "- SEARCH INTENT ALIGNMENT: This post is indexed but receives zero impressions. Re-align the title and opening paragraphs directly with primary search intent. Provide direct, informative answers in the first 200 words.",
    FLAG_THIN_CONTENT: "- CONTENT EXPANSION (Thin Content): The article is under 400 words. Expand the text significantly (target 800-1200 words) by adding historical context, key examples, artistic techniques, and analytical insights without adding filler.",
    FLAG_CRAWLED_NOT_INDEXED: "- QUALITY OVERHAUL (Crawled - Not Indexed): Google evaluated this post and chose not to index it due to insufficient value. Rewrite the article completely to offer unique, authoritative perspectives, original synthesis, and rich educational value.",
    FLAG_NO_TOP_KEYWORD: "- ENTITY & KEYWORD CLARITY: Google cannot associate primary keywords with this page. Clearly define and reinforce the main topic/term throughout the intro, subheadings, and body text using clear LSI keywords."
}



def generate_llm_prompt(bitmask: int, title: str, body: str) -> str:
    active_instructions = []

    # 1. Iterate over dictionary keys and evaluate bitwise AND
    for flag_bit, instruction in PROMPT_MODULES.items():
        if bitmask & flag_bit:
            active_instructions.append(instruction)

    # Fallback if no specific prompt flags were matched
    if not active_instructions:
        active_instructions.append("- GENERAL REFINEMENT: Polish readability, flow, and structural layout.")

    # 2. Join matched instructions into a multi-line string
    remediation_block = "\n".join(active_instructions)

    # 3. Construct the complete prompt layout
    full_prompt = f"""### SYSTEM INSTRUCTION
You are an expert SEO content strategist and art history editor for freyartt.com.
Your task is to rewrite, expand, and structure the provided blog post into high-quality Markdown format.
All posts should be written in Turkish.

RULES:
- Preserve the authentic, expert tone of Freya Art Route. 
- Tone & Language: Human-written tone, informative, engaging, concise sentences. NO AI fluff or filler.
- Word Count: Target length of 800-1200 words.
- Keywords: Naturally integrate the primary keywords: 'Sanat tarihi platformu', 'Sanat tarihi', 'sanat akımları'.
- Formatting: Use clean Markdown with short paragraphs and semantic ## (H2) and ### (H3) subheadings.
- IMAGES: You MUST retain ALL existing images from the original text in their approximate relative locations. Preserve the original image URLs and exact alt text tags using standard Markdown syntax: ![Exact Original Alt Text](Image URL).
- Output: Return ONLY the raw updated Markdown body. Do NOT include intro/outro chatter or ```markdown code block fences.


---
### REQUIRED REMEDIATION FIXES:
{remediation_block}

---
### ARTICLE TO REWRITE:
TITLE: {title}

BODY:
{body}
"""
    return full_prompt