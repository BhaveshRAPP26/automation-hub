"""
app.py

Streamlit interface for OneTrust Consent Mode QA.
"""


import streamlit as st

from qa_runner import OneTrustQARunner

from report import generate_reports



############################################################
# Page configuration
############################################################


st.set_page_config(

    page_title="OneTrust Consent Mode QA",

    page_icon="🔍",

    layout="wide"

)



############################################################
# Header
############################################################


st.title(
    "🔍 OneTrust Consent Mode QA Automation"
)


st.write(

"""
This tool automates OneTrust Consent Mode validation
using Playwright.

It validates:

- DataLayer OneTrustGroupsUpdated events
- OnetrustActiveGroups values
- GA4 network requests
- Consent acceptance behaviour
- Consent rejection behaviour
- Navigation behaviour

"""

)



############################################################
# Sidebar
############################################################


with st.sidebar:


    st.header(
        "Settings"
    )


    headless = st.checkbox(

        "Run browser headless",

        value=False

    )


    screenshots = st.checkbox(

        "Capture screenshots",

        value=True

    )


    st.info(

        """
Chrome/Chromium browser will be
controlled using Playwright.

"""

    )



############################################################
# URL Input
############################################################


st.subheader(
    "URLs to Test"
)



urls_input = st.text_area(

    "Enter one URL per line",

    height=150,

    placeholder="""
https://www.example.com
https://www.example2.com
"""

)



############################################################
# Run QA
############################################################


if st.button(
    "▶ Run OneTrust QA",
    type="primary"
):


    urls = [

        x.strip()

        for x in urls_input.split("\n")

        if x.strip()

    ]


    if len(urls)==0:


        st.warning(
            "Please enter at least one URL."
        )


        st.stop()



    all_results = []



    progress = st.progress(
        0
    )


    status_box = st.empty()



    for index,url in enumerate(urls):


        status_box.info(

            f"Running QA for: {url}"

        )


        runner = OneTrustQARunner(

            url=url,

            screenshots=screenshots

        )


        results = runner.run()


        all_results.extend(
            results
        )


        progress.progress(

            int(
                (
                    index+1
                )
                /
                len(urls)
                *
                100
            )

        )



    status_box.success(

        "QA execution completed."

    )



    ########################################################
    # Results display
    ########################################################


    st.divider()


    st.subheader(
        "QA Results"
    )


    import pandas as pd


    df = pd.DataFrame(
        all_results
    )


    display_columns = [
    "step",
    "action",
    "current_url",
    "active_groups",
    "ga_event",
    "ga_requests",
    "status",
    "notes"
    ]

    st.dataframe(

    df[display_columns],

    use_container_width=True,

    hide_index=True

    )



    ########################################################
    # Reports
    ########################################################


    st.divider()


    st.subheader(

        "Reports"

    )



    reports = generate_reports(

        all_results

    )


    excel_file = reports["excel"]


    html_file = reports["html"]



    with open(
        excel_file,
        "rb"
    ) as f:


        st.download_button(

            label="📊 Download Excel Report",

            data=f,

            file_name=
            excel_file.name,

            mime=
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

        )



    with open(
        html_file,
        "rb"
    ) as f:


        st.download_button(

            label="🌐 Download HTML Report",

            data=f,

            file_name=
            html_file.name,

            mime=
            "text/html"

        )



############################################################
# Footer
############################################################


st.divider()


st.caption(

"""
OneTrust Consent Mode QA Framework
Built using Streamlit + Playwright + Python

"""

)