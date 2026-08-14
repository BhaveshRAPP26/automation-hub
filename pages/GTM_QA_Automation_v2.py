from pages.gtm_qa_automation import request_extractor as gq
import streamlit as st
import asyncio
import os
import re


st.set_page_config(layout="wide")
st.title("Website GTM QA")

st.header("Part 1")


def reconstruct_url(filename):
    """
    Reconstruct the URL from the uploaded text file name.

    Example:
        a_b_d_com_p1_p2_p3_p4_ids.txt
    becomes:
        https://a.b.d.com/p1/p2-p3-p4

    Convention:
        - First 4 underscore-separated parts = domain
        - 5th part = first URL path segment
        - Remaining parts = joined with '-'
    """
    name = os.path.basename(filename)

    # Remove the _ids.txt suffix
    if not name.lower().endswith("_ids.txt"):
        raise ValueError(
            f"Invalid file name '{name}'. "
            "Expected a file name ending in '_ids.txt'."
        )

    name_without_suffix = re.sub(r"_ids\.txt$", "", name, flags=re.IGNORECASE)
    parts = name_without_suffix.split("_")

    if len(parts) < 4:
        raise ValueError(
            f"Invalid file name '{name}'. "
            "At least 4 underscore-separated parts are required for the domain."
        )

    # First 4 parts form the domain
    domain = ".".join(parts[:4])

    # Remaining parts form the path
    path_parts = parts[4:]

    if not path_parts:
        return f"https://{domain}"

    # Based on the supplied naming convention:
    # p1_p2_p3_p4 -> /p1/p2-p3-p4
    if len(path_parts) == 1:
        path = path_parts[0]
    else:
        path = f"{path_parts[0]}/" + "-".join(path_parts[1:])

    return f"https://{domain}/{path}"


uploaded_files = st.file_uploader(
    "Upload GTM QA ID text file(s)",
    type=["txt"],
    accept_multiple_files=True,
    help=(
        "Upload files using the naming convention "
        "'a_b_d_com_p1_p2_p3_p4_ids.txt'. "
        "The URL will be reconstructed from the file name."
    ),
)

if uploaded_files:
    st.subheader("URLs to be tested")

    file_details = []

    for uploaded_file in uploaded_files:
        try:
            url = reconstruct_url(uploaded_file.name)
            file_details.append(
                {
                    "File": uploaded_file.name,
                    "Reconstructed URL": url,
                    "Status": "Ready",
                }
            )
        except ValueError as e:
            file_details.append(
                {
                    "File": uploaded_file.name,
                    "Reconstructed URL": "",
                    "Status": str(e),
                }
            )

    st.dataframe(file_details, use_container_width=True)

    if st.button("Launch QA"):
        for uploaded_file in uploaded_files:
            try:
                url = reconstruct_url(uploaded_file.name)

                # The second program currently expects the interaction IDs
                # in a file named "ids.txt". Replace that file for each URL.
                with open("ids.txt", "wb") as f:
                    f.write(uploaded_file.getvalue())

                ids_list = uploaded_file.getvalue().decode("utf-8").splitlines()

                st.write(f"Launching QA for: {url}")

                # request_extractor.main() is still called with the URL,
                # while ids.txt contains the IDs for this specific URL.
                result = asyncio.run(gq.main(url, ids_list))




                if result:
                    st.download_button(
                        label=f"Download JSON - {uploaded_file.name}",
                        data=result["content"],
                        file_name=result["filename"],
                        mime="application/json",
                        key=f"download_{uploaded_file.name}"
                    )

            except ValueError as e:
                st.error(f"{uploaded_file.name}: {e}")
            except Exception as e:
                st.error(
                    f"QA failed for {uploaded_file.name}: {e}"
                )
