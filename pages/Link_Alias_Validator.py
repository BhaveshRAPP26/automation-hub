import streamlit as st
import pandas as pd
st.title('Link Alias')
link_alias_input = st.text_area('Enter Link Alias',placeholder="Enter Value")
st.button("Submit",on_click=lambda:url_split(link_alias_input))
output_area = st.container()  # Ensures everything renders below the button


def url_split(n):
  with output_area.container():
    if not n.strip():
        st.error("ERROR: No input provided.")  
        return
    n=n.strip()
    line_split = str(n).splitlines()
    new_list=[]
    for i in range(len(line_split)):
        line_split[i]=line_split[i].strip()
        word_split= line_split[i].split("_")
        new_list.append(word_split)
    check(new_list)

def transposing_list(new_list):
  transposed_matrix = [[row[i] for row in new_list] for i in range(len(new_list[0]))]  
  defining_df(transposed_matrix)  

def check(n):
  with output_area.container():
    count_fail=0
    count_pass=0
    for i in range(len(n)):
        if len(n[i]) != 12:
            st.error(f"ERROR: {12-len(n[i])} parameters missing in {i+1} alias")
            count_fail = 1
        else:
            for j in range(len(n[i])):
                if not n[i][j].strip():
                    st.warning(f"WARNING: Empty String at {j+1} position in {i+1} alias")
                elif ' ' in n[i][j]:
                    st.warning(f"WARNING: {n[i][j]} at {j+1} position in alias {i+1} contains a space")
    if count_fail==0:
        st.success("Parameters count for all aliases is good :)")
        transposing_list(n)
    

def defining_df(n):
  with output_area.container():
    key = ['journey_stage','brand','business_unit','module_type','module_concept','product','feature','module_position','link_position','content_desk','link_type','node_id']
    def_dict = dict(zip(key,n))
    def_df= pd.DataFrame.from_dict(def_dict,orient='index')
    def_df.columns = range(1, def_df.shape[1] + 1)  # ➕ Start columns from 1
    st.write(def_df)











