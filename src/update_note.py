"""
# Update Note Module
This module provides functionality to update a VPP Note based on recent notes and new documents.

- Author: Liam Branch
- Copyright (c) N-Power Medicine, 2025
"""

import pypdfium2 as pdfium
import io, base64, os
from databricks_langchain import ChatDatabricks
from langchain_core.prompts import SystemMessagePromptTemplate, HumanMessagePromptTemplate, ChatPromptTemplate

# Get the directory where this file is located
SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def create_chat_prompt():
    """Create the chat prompt for VPP Note update."""
    with open(os.path.join(SRC_DIR, "vpp_guidelines.md"), "r") as f:
        vpp_manual = f.read()
    
    system_prompt = SystemMessagePromptTemplate.from_template(
        """You are a VPP (Virtual Physician Partner) who is helpful, precise, accurate, good at analyzing medical documents. You will be given VPP guidelines, reports with their creation dates, and the most recent VPP Note. Your goal is to append to the most recent VPP Note to update it with any new information from the reports.

    VPP Guidelines Begin...
    {vpp_guidelines}
    ...Guidelines End.""", 
        partial_variables={'vpp_guidelines': vpp_manual})
    
    human_ask = HumanMessagePromptTemplate.from_template(
        """The most recent VPP Note starts...
    {most_recent_note}
    ...Note Ends.

    First summarize each document, then update this most recent VPP note based on the VPP guidelines, given today is {current_day}. Update the One-Liner if applicable. Correct formatting issues. Do not give a justification after VPP note.""")

    conversation = ChatPromptTemplate.from_messages([
        system_prompt,
        ("placeholder", "{HIL_pdfs}"),
        human_ask
    ])
    return conversation


def pdf_pages_b64(path: str, pages=3, dpi=300):
    """Convert PDF pages to base64 encoded PNG images."""
    try:
        doc, out, scale = pdfium.PdfDocument(path), [], dpi/72
        for i in range(min(pages, len(doc))):
            buf = io.BytesIO()
            doc[i].render(scale=int(scale)).to_pil().save(buf, format="PNG")
            out.append("data:image/png;base64,"+base64.b64encode(buf.getvalue()).decode())
        doc.close()
        return out
    except Exception as e:
        return [f"Processing failed: {e}"]


def prepare_docs_for_prompt(image_base64_list: list) -> list:
    """Prepare documents for the prompt."""
    if len(image_base64_list) > 80:
        print(f"Warning: Processing {len(image_base64_list)} pages")
    if len(image_base64_list) >= 100:
        raise ValueError("Too many documents! Reduce PDF length")

    return [
         {"type": "text", "text": "Documents Begin..."},
         *[{"type": "image_url", "image_url": {"url": image_data}}
           for image_data in image_base64_list],
         {"type": "text", "text": "Documents End.."}]


def prepare_chain(
    model_endpoint: str = 'databricks-claude-sonnet-4-5',
    temperature: float = 0.0,
    max_tokens: int = 5000
):
    """
    Prepare the chain for append operation.
    Args:
        model_endpoint (str): Model to use
        temperature (float): Sampling temperature
        max_tokens (int): Max output tokens
    """
    model = ChatDatabricks(
        endpoint=model_endpoint,
        temperature=temperature,
        max_tokens=max_tokens
    )
    
    conversation = create_chat_prompt()
    return conversation | model


def append_to_vpp_note(
    most_recent_note, 
    most_recent_note_date, 
    current_day, 
    page_images,
    model_endpoint: str = 'databricks-claude-sonnet-4-5',
    temperature: float = 0.0,
    max_tokens: int = 5000
) -> tuple:
    """
    Append to the VPP Note.
    Args:
        most_recent_note (str): The most recent VPP Note
        most_recent_note_date (str): Date of the most recent note
        current_day (str): Current date
        page_images (list): Base64 encoded images
        model_endpoint (str): Model to use
        temperature (float): Sampling temperature
        max_tokens (int): Max output tokens
    Returns:
        tuple: (updated_note, metadata)
    """
    append_chain = prepare_chain(model_endpoint, temperature, max_tokens)
    
    # Flatten nested lists
    flattened_page_images = [
        item if isinstance(sublist, list) else sublist
        for sublist in page_images
        for item in (sublist if isinstance(sublist, list) else [sublist])
    ]
    
    state = {
        "most_recent_note": str(most_recent_note),
        "most_recent_note_date": str(most_recent_note_date),
        "current_day": str(current_day),
        "HIL_pdfs": [("human", prepare_docs_for_prompt(flattened_page_images))],
    }
    
    try:
        message = append_chain.invoke(state)
        return message.content, message.response_metadata
    except Exception as e:
        out = f"Error processing VPP Note: {str(e)}"
        metadata = {"error": str(e)}
        return out, metadata