"""
# Style Transfer Module
This module provides functionality to process medical notes into VPP format.
LangChain is used to interact with Databricks endpoints for style transfer.

- Author: Liam Branch
- Copyright (c) N-Power Medicine, 2025
"""

import os, re, base64
from typing import Optional, TypedDict
from databricks_langchain import ChatDatabricks
from langgraph.graph import END, StateGraph, START
from langchain_core.prompts import PromptTemplate, SystemMessagePromptTemplate, ChatPromptTemplate

# Get the directory where this file is located
SRC_DIR = os.path.dirname(os.path.abspath(__file__))


def create_style_transfer_prompts():
    """Create the chat prompt for the VPP Note update."""
    # Read files using absolute paths
    with open(os.path.join(SRC_DIR, "vpp_guidelines.md"), "r") as f:
        vpp_manual = f.read()
    with open(os.path.join(SRC_DIR, "special_instructions.md"), "r") as f:
        sp_instructions = f.read()
    with open(os.path.join(SRC_DIR, "date_instructions.md"), "r") as f:
        date_instructions = f.read()

    system_prompt = SystemMessagePromptTemplate.from_template(
        """You are a VPP (Virtual Physician Partner) who is helpful, precise, accurate, good at analyzing medical notes. You will be given VPP guidelines, a Med Onc Visit Note, and the date. Your goal is to re-write the Med Onc Visit Note in the style defined in the VPP Guidelines.

    VPP Guidelines Begin...
    {vpp_guidelines}
    ...Guidelines End.

    Special Instructions Begin...
    {special_instructions}
    Instructions End.""",
        partial_variables={
            "special_instructions": sp_instructions,
            "vpp_guidelines": vpp_manual
        })

    conversation1 = ChatPromptTemplate.from_messages([
        system_prompt,
        ("placeholder", "{HIL_pdfs}"),
        ("human", "Write a VPP Styled Med Onc Visit Note.")
    ])

    corrective_judge_prompt = SystemMessagePromptTemplate.from_template(
        """Given a generated VPP note and the Med Onc Visit note it was derived from, determine if the VPP note missed any key information. If so, list out missing events in the format of the VPP note. Then update the VPP note to include the missing events and include only Brief One-Liner, Detailed One-Liner, Disease Header, Oncologic History (in chronological order).

    VPP Note Begin...
    {needs_correction}
    ...Note End.

    Special Instructions Begin...
    {special_instructions}
    Instructions End.""", 
        partial_variables={"special_instructions": sp_instructions})

    conversation2 = ChatPromptTemplate.from_messages([
        corrective_judge_prompt,
        ("placeholder", "{wild_note}"),
    ])

    formatting_judge_prompt = PromptTemplate.from_template(
        """Given a VPP styled Med Onc Visit note, determine if it contains any structural issues or irrelevant content. If so, list out formatting issues. If issues are present, re-write the VPP note to fix these formatting issues, otherwise re-write as seen. Make sure the re-written VPP note contains only Brief One-Liner, Detailed One-Liner, Disease Header, Oncologic History (in chronological order) and once written the response has no comments afterwards.

    VPP Note Begin...
    {needs_formatting}
    ...Note End.

    Special Guidelines Begin...
    {formatting_instructions}
    Guidelines End.""", 
        partial_variables={"formatting_instructions": date_instructions + sp_instructions})

    return conversation1, conversation2, formatting_judge_prompt


def prepare_style_transfer_graph(
    model_endpoint: str = 'databricks-claude-sonnet-4-5',
    temperature: float = 0.0,
    max_tokens: int = 5000
):
    """
    Prepare the graph for style transfer operation.
    Args:
        model_endpoint (str): Databricks model endpoint name
        temperature (float): Sampling temperature (0.0-1.0)
        max_tokens (int): Maximum tokens to generate
    """
    model = ChatDatabricks(
        endpoint=model_endpoint,
        temperature=temperature,
        max_tokens=max_tokens
    )

    conversation, correct_prompt, fmt_prompt = create_style_transfer_prompts()

    class CustomState(TypedDict):
        wild_note: str
        wild_note_date: str
        initial_note: list[dict]
        messages: list[dict]
        needs_correction: Optional[str]
        needs_formatting: Optional[str]
        correct_and_formatted: Optional[str]
        vpp_note: Optional[str]

    style_transfer_chain = conversation | model
    judge_chain = correct_prompt | model
    formatting_chain = fmt_prompt | model

    def style_transfer_node(state: CustomState) -> CustomState:
        result = style_transfer_chain.invoke({"HIL_pdfs": state["initial_note"]})
        state["needs_correction"] = result.content
        return state

    def judge_corrections(state: CustomState) -> CustomState:
        result = judge_chain.invoke({
            "needs_correction": state["needs_correction"],
            "wild_note": state["initial_note"]
        })
        state["needs_formatting"] = result.content
        return state

    def judge_formatting(state: CustomState) -> CustomState:
        result = formatting_chain.invoke({"needs_formatting": state["needs_formatting"]})
        state["correct_and_formatted"] = result.content

        try:
            if (bool(re.search(r'(?i)Brief One-Liner:', state["correct_and_formatted"])) and
                bool(re.search(r'(?i)Detailed One-Liner:', state["correct_and_formatted"]))):
                state["vpp_note"] = state["correct_and_formatted"]
            elif (bool(re.search(r'(?i)Brief One-Liner:', state["needs_formatting"])) and
                  bool(re.search(r'(?i)Detailed One-Liner:', state["needs_formatting"]))):
                state["vpp_note"] = state["needs_formatting"]
            else:
                state["vpp_note"] = state["needs_correction"]

            state["vpp_note"] = state["vpp_note"].strip()
        except Exception as e:
            state["vpp_note"] = f"Error: {e}"

        return state

    builder = StateGraph(CustomState)
    builder.add_node("style_transfer", style_transfer_node)
    builder.add_node("reflect_corrections", judge_corrections)
    builder.add_node("reflect_formatting", judge_formatting)
    builder.add_edge(START, "style_transfer")
    builder.add_edge("style_transfer", "reflect_corrections")
    builder.add_edge("reflect_corrections", "reflect_formatting")
    builder.add_edge("reflect_formatting", END)
    
    return builder.compile()


def prepare_pdf_note_for_prompt(image_base64_list: list, note_date: str) -> list:
    """Prepare PDF pages for the prompt."""
    if len(image_base64_list) > 80:
        print(f"Warning: Processing {len(image_base64_list)} pages")
    if len(image_base64_list) >= 100:
        raise ValueError("Too many documents! Reduce PDF length")

    return [
        {"type": "text", "text": f"Med Onc Visit Note written on {note_date} Begins..."},
        *[{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(img).decode()}}
          for img in image_base64_list],
        {"type": "text", "text": "Med Onc Visit Note Ends.\n\n"},
    ]


def prepare_text_note_for_prompt(note_text: str, note_date: str) -> list:
    """Prepare text note for the prompt."""
    return [
        {"type": "text", "text": f"Med Onc Visit Note written on {note_date} Begins...\n\n{note_text}\n\nMed Onc Visit Note Ends."}
    ]


def execute_style_transfer(
    page_images: list, 
    date: str, 
    model_endpoint: str = 'databricks-claude-sonnet-4-5',
    temperature: float = 0.0,
    max_tokens: int = 5000
) -> str:
    """
    Execute style transfer with image input (IMAGES mode).
    Args:
        page_images (list): Base64 encoded images
        date (str): Note date
        model_endpoint (str): Model to use
        temperature (float): Sampling temperature
        max_tokens (int): Max output tokens
    """
    graph = prepare_style_transfer_graph(model_endpoint, temperature, max_tokens)
    initial_note = prepare_pdf_note_for_prompt(page_images, date)

    state = {
        "messages": [{"role": "user", "content": "Process medical note to VPP format."}],
        "wild_note_date": date,
        "initial_note": [("human", initial_note)]
    }

    try:
        result_state = graph.invoke(state)
        return result_state["vpp_note"]
    except Exception as e:
        return f"Error processing VPP Note: {str(e)}"


def execute_style_transfer_text(
    note_text: str, 
    date: str, 
    model_endpoint: str = 'databricks-claude-sonnet-4-5',
    temperature: float = 0.0,
    max_tokens: int = 5000
) -> str:
    """
    Execute style transfer with text input (TEXT mode).
    Args:
        note_text (str): Input text
        date (str): Note date
        model_endpoint (str): Model to use
        temperature (float): Sampling temperature
        max_tokens (int): Max output tokens
    """
    graph = prepare_style_transfer_graph(model_endpoint, temperature, max_tokens)
    initial_note = prepare_text_note_for_prompt(note_text, date)

    state = {
        "messages": [{"role": "user", "content": "Process medical note to VPP format."}],
        "wild_note_date": date,
        "initial_note": [("human", initial_note)]
    }

    try:
        result_state = graph.invoke(state)
        return result_state["vpp_note"]
    except Exception as e:
        return f"Error processing VPP Note: {str(e)}"