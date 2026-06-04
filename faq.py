import streamlit as st


FAQ_ITEMS = [
    {
        "question": "I want to download the logs for a past event. How do I do it?",
        "answer": """
Go to **Create / Switch Event**, select the past event, and switch to that event.

Then go back to **Queue Log / Export CSV** and click **Download CSV**.
        """,
    },
    {
        "question": "How do I delete past events?",
        "answer": """
This needs to be done from the backend database.

It is not available in this interface to prevent accidental deletion.
        """,
    },
    {
        "question": "How do I search the logs for a previous user?",
        "answer": """
Under **Queue Log / Export CSV**, use the search button at the top right of the table.
        """,
    },
    {
        "question": "Why can’t I delete people in the queue?",
        "answer": """
This is to prevent accidental clicks, especially when users are scrolling on mobile.

If someone should be cleared, wait for the next available toilet, assign the person, then click **Return**.
        """,
    },
    {
        "question": "What happens when I assign a person to a toilet?",
        "answer": """
The person’s queue card will change to **IN PROGRESS**.

It will also briefly nudge in red. You can click **Nudge** again to trigger the animation again.
        """,
    },
]


def render_faq():
    with st.expander("❓ FAQ / Help"):
        for item in FAQ_ITEMS:
            st.markdown(f"**{item['question']}**")
            st.markdown(item["answer"])
            st.markdown("---")