# examples/document_editor_logic.py
# Logic implementations for the DocumentEditor class, following snake_case.

import logging


def set_content(i, ctx, e, ad):
    """Sets the initial content of the document."""
    ctx["content"] = e.payload.get("content", "")
    logging.info(f"✍️ Document content set to: '{ctx['content']}'")


def update_content(i, ctx, e, ad):
    """Appends a character to the document's content."""
    ctx["content"] += e.payload.get("key", "")
    logging.info(f"✍️ Content updated: '{ctx['content']}'")


def enter_format_mode(i, ctx, e, ad):
    """Logs entry into the formatting sub-state."""
    logging.info("🎨 Entered formatting mode.")


def toggle_bold(i, ctx, e, ad):
    """Toggles the 'isBold' flag in the context."""
    ctx["isBold"] = not ctx["isBold"]
    logging.info(f"** Toggled Bold: {'ON' if ctx['isBold'] else 'OFF'} **")


def log_entry(i, ctx, e, ad):
    """Logs a message upon entering the parent 'editing' state."""
    logging.info("➡️  Entering 'editing' state.")


def log_exit(i, ctx, e, ad):
    """Logs a message upon exiting the parent 'editing' state."""
    logging.info("⬅️  Exiting 'editing' state.")


def save_document(i, ctx, e):
    """
    A synchronous service that 'saves' the document.

    Raises:
        ValueError: If the content is too short to be saved.

    Returns:
        Dict[str, Any]: A dictionary with the save status and content length.
    """
    content_to_save = ctx.get("content", "")
    logging.info(f"💾 Saving document with content: '{content_to_save}'...")
    if len(content_to_save) < 5:
        raise ValueError("Content too short to save!")
    logging.info("✅ Document saved successfully.")
    return {"status": "saved", "length": len(content_to_save)}
