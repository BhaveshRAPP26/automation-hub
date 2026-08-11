# print("\n\nevent name =",input("Enter request: ").split("&en=")[1].split("&")[0].replace("%20"," "))

import streamlit as st

def comparison(req1,req2,delim):
      
    req1_params = req1.split("&")
    req2_params = req2.split("&")

    if len(req1_params) == len(req2_params):
        st.text("Number of parameters same? Yes")
        st.text("Non-identical parameters below:") 
        unequal_params_id = []
        for i in range(len(req1_params)):
            if req1_params[i] != req2_params[i]:
                unequal_params_id.append(i)
                #print("false: " + str(req1_params[i]))

        for index in unequal_params_id:
            req1_p = req1_params[index].split("=")[0]
            req1_val = req1_params[index].split("=")[1]

            req2_p = req2_params[index].split("=")[0]
            req2_val = req2_params[index].split("=")[1]
            
            st.text(req1_p + ": " + req1_val + ", " + req2_p + ": " + req2_val) 

    else:
        st.text("Number of parameters same? No")


def split_param(req,delim):
    st.text(req.split(delim)[1].split("&")[0].replace("%20"," "))




st.set_page_config(layout='wide')
st.title("Program Title")

st.header("Part 1")

requests = st.text_area("Paste one single property, and one global property here", height=150)

if st.button("Validate"):
    req1 = requests.split("\n")[0]
    req2 = requests.split("\n")[1]

    split_param(req1,"&tid=")
    split_param(req1,"&en=")

    split_param(req2,"&tid=")
    split_param(req2,"&en=")

    comparison(req1,req2,"&_p=")



