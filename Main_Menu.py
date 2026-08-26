import streamlit as st
from pathlib import Path
from automation_registry import AUTOMATIONS
from gemini_helper import identify_automation
import json

# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Analytics Automation Hub",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            display: none;
        }

        [data-testid="stSidebarCollapsedControl"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# SESSION STATE
# ============================================================

if "recent_automations" not in st.session_state:
    st.session_state.recent_automations = []

if "favourites" not in st.session_state:
    st.session_state.favourites = []


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def launch_automation(automation):
    """
    Navigate to the selected Streamlit page.
    """

    page_path = Path(automation["page"])

    if page_path.exists():

        # Store in recent history
        automation_id = automation["id"]

        if automation_id in st.session_state.recent_automations:
            st.session_state.recent_automations.remove(
                automation_id
            )

        st.session_state.recent_automations.insert(
            0,
            automation_id
        )

        # Keep only the five most recent
        st.session_state.recent_automations = (
            st.session_state.recent_automations[:5]
        )

        st.switch_page(str(page_path))

    else:
        st.error(
            f"Automation page could not be found:\n\n"
            f"`{automation['page']}`"
        )


def toggle_favourite(automation_id):

    if automation_id in st.session_state.favourites:

        st.session_state.favourites.remove(
            automation_id
        )

    else:

        st.session_state.favourites.append(
            automation_id
        )


def get_filtered_automations(
    search_term,
    category,
    tag
):

    results = []

    for automation in AUTOMATIONS:

        # Search
        if search_term:

            search_text = " ".join([
                automation["name"],
                automation["description"],
                automation["category"],
                automation["input"],
                automation["output"],
                " ".join(automation["tags"])
            ]).lower()

            if search_term.lower() not in search_text:
                continue

        # Category
        if category != "All":

            if automation["category"] != category:
                continue

        # Tag
        if tag != "All":

            if tag not in automation["tags"]:
                continue

        results.append(automation)

    return results


def render_automation_card(automation):

    is_favourite = (
        automation["id"]
        in st.session_state.favourites
    )

    with st.container(border=True):

        # Header
        col1, col2 = st.columns([5, 1])

        with col1:

            st.markdown(
                
                f"{automation['name']}"
            )

        with col2:

            favourite_label = (
                "★" if is_favourite else "☆"
            )

            if st.button(
                favourite_label,
                key=f"fav_{automation['id']}",
                help="Add to favourites"
            ):

                toggle_favourite(
                    automation["id"]
                )

                st.rerun()

        # Description
        st.write(
            automation["description"]
        )

        # Metadata
        st.markdown(
            f"""
            **Input:** {automation["input"]}  
            **Output:** {automation["output"]}  
            **Scope:** {automation["scope"]}
            """
        )

        # Tags
        tags = " ".join(
            f"`{tag}`"
            for tag in automation["tags"]
        )

        st.markdown(tags)

        st.write("")

        if st.button(
            "Launch Automation →",
            key=f"launch_{automation['id']}",
            type="primary"
        ):

            launch_automation(automation)





# ============================================================
# MAIN PAGE
# ============================================================

st.markdown(
    """
    <h1 style="margin-bottom:0;">
        ⚡ Analytics Automation Hub
    </h1>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <p style="font-size:1.1rem; color:#777;">
        Automate repetitive Analytics Enablement tasks,
        QA processes and data preparation workflows.
    </p>
    """,
    unsafe_allow_html=True
)

# ============================================================
# GEMINI API KEY
# ============================================================

st.markdown("### 🔑 Gemini API Key")

st.markdown(
    """
    <style>
    button[data-testid="stTextInputRevealButton"] {
        display: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = ""

gemini_api_key = st.text_input(
    "Enter your Gemini API key",
    type="password",
    value=st.session_state["gemini_api_key"],
    placeholder="Paste your Gemini API key here",
    label_visibility="collapsed"
)

st.session_state["gemini_api_key"] = gemini_api_key

if gemini_api_key:
    st.success("Gemini API key entered.")


# ============================================================
# AI ASSISTANT
# ============================================================

st.markdown("## 🤖 AI Assistant")

st.write(
    "Describe what you want to accomplish and "
    "the AI Assistant will recommend the appropriate "
    "automation."
)


col1, col2 = st.columns(
    [5, 1]
)


with col1:

    ai_prompt = st.text_input(
        "Request",
        placeholder=(
            "e.g. I have a list of URLs and want to check "
            "their UTM parameters"
        ),
        label_visibility="collapsed"
    )


with col2:

    ask_ai = st.button(
        "Ask AI →",
        type="primary",
        use_container_width=True
    )


# ============================================================
# PROCESS REQUEST
# ============================================================

if ask_ai:

    if not gemini_api_key:

        st.warning(
            "Please enter your Gemini API key first."
        )

    elif not ai_prompt.strip():

        st.warning(
            "Please enter a request first."
        )

    else:

        with st.spinner(
            "Finding the best automation..."
        ):

            try:

                result = identify_automation(
                    ai_prompt,
                    st.session_state["gemini_api_key"]
                )

                result = result.replace(
                    "```json",
                    ""
                ).replace(
                    "```",
                    ""
                ).strip()

                ai_result = json.loads(result)

                st.session_state["ai_result"] = ai_result

            except Exception as e:

                st.error(
                    f"Unable to process the request: {e}"
                )


# ============================================================
# DISPLAY RESULT
# ============================================================

if "ai_result" in st.session_state:

    result = st.session_state["ai_result"]

    if result.get("result") == "MATCH":

        automation_id = result.get(
            "recommended_automation"
        )

        # Find automation in local registry
        automation = next(
            (
                a for a in AUTOMATIONS
                if a["id"] == automation_id
            ),
            None
        )

        if automation:

            st.success(
                f"Recommended automation: "
                f"**{automation['name']}**"
            )

            # Confidence
            confidence = result.get(
                "confidence",
                "UNKNOWN"
            )

            st.info(
                f"Confidence: {confidence}\n\n"
                f"Reason: {result.get('reason', '')}"
            )

            # Launch button
            if st.button(
                f"Launch {automation['name']} →",
                type="primary"
            ):

                launch_automation(
                    automation
                )

        else:

            st.error(
                "Gemini recommended an automation that "
                "could not be found in the local registry."
            )

    elif result.get("result") == "NO_MATCH":

        st.warning(
            "I couldn't find an existing automation "
            "that directly matches this request."
        )

        st.info(
            result.get(
                "reason",
                ""
            )
        )

    else:

        st.warning(
            "The AI returned an unexpected response."
        )

        st.json(result)

# ============================================================
# CATALOGUE CONTROLS
# ============================================================

st.markdown("## 📚 Automation Catalogue")

search_col, category_col, tag_col = st.columns(
    [2, 1, 1]
)

with search_col:

    search_term = st.text_input(
        "🔎 Search",
        placeholder=(
            "Search by name, purpose, technology..."
        ),
        label_visibility="collapsed"
    )

with category_col:

    categories = sorted(
        set(
            automation["category"]
            for automation in AUTOMATIONS
        )
    )

    selected_category = st.selectbox(
        "Category",
        ["All"] + categories,
        label_visibility="collapsed"
    )

with tag_col:

    tags = sorted(
        set(
            tag
            for automation in AUTOMATIONS
            for tag in automation["tags"]
        )
    )

    selected_tag = st.selectbox(
        "Technology / Tag",
        ["All"] + tags,
        label_visibility="collapsed"
    )


# ============================================================
# FILTER AUTOMATIONS
# ============================================================

filtered_automations = get_filtered_automations(
    search_term,
    selected_category,
    selected_tag
)


# ============================================================
# DISPLAY RESULTS BY CATEGORY
# ============================================================

if not filtered_automations:

    st.warning(
        "No automations match your search criteria."
    )

else:

    # Preserve category order
    category_order = []

    for automation in AUTOMATIONS:

        category = automation["category"]

        if (
            category not in category_order
            and any(
                a["category"] == category
                for a in filtered_automations
            )
        ):

            category_order.append(category)


    for category in category_order:

        category_automations = [
            automation
            for automation in filtered_automations
            if automation["category"] == category
        ]

        st.markdown(
            f"### {category}"
        )

        # Three-column grid
        for i in range(
            0,
            len(category_automations),
            3
        ):

            row = category_automations[
                i:i + 3
            ]

            columns = st.columns(
                3
            )

            for column, automation in zip(
                columns,
                row
            ):

                with column:

                    render_automation_card(
                        automation
                    )

        st.write("")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Analytics Enablement • Automation Hub"
)