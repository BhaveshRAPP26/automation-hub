import streamlit as st
import pandas as pd



def time_converter(hours, minutes,seconds):
    
    final_hours = ""
    final_minutes = ""
    final_seconds = ""

    if len(str(hours)) == 1:
        final_hours = "0" + str(hours)
    else:
        final_hours = str(hours)

    if len(str(minutes)) == 1:
        final_minutes = "0" + str(minutes)
    else:
        final_minutes = str(minutes)

    if len(str(seconds)) == 1:
        final_seconds = "0" + str(seconds)
    else:
        final_seconds = str(seconds)
    
    return final_hours + ":" + final_minutes + ":" + final_seconds

def input_validator(time):
    
    if ":" not in time or len(time.split(":")) > 3 or "" in time.split(":"):
        st.warning('Please enter a valid video duration', icon="⚠️")
        return False
    return True
    
def transformation(time):
    overall_time = time.split(":")
    hours_to_seconds = 0
    minutes_to_seconds = 0
    seconds = 0

    if len(overall_time) == 3:
        hours_to_seconds = int(overall_time[0]) * 3600
        minutes_to_seconds = int(overall_time[1]) * 60
        seconds = int(overall_time[2]) 

    if len(overall_time) == 2:
        minutes_to_seconds = int(overall_time[0]) * 60
        seconds = int(overall_time[1])
    
    total_seconds = hours_to_seconds + minutes_to_seconds + seconds

    percentages_in_seconds = []

    for pct in percentages:
        percentages_in_seconds.append(pct*total_seconds)

    final_values = []
    for i in range(len(percentages_in_seconds)):
        hours = int(percentages_in_seconds[i] // 3600)
        minutes = int(percentages_in_seconds[i] // 60)
        remaining_seconds = int(percentages_in_seconds[i] % 60)

        final_values.append(time_converter(hours,minutes,remaining_seconds))

    # st.text(f"{percentages[i]} = {hours}:{minutes}:{remaining_seconds}")

    df = pd.DataFrame(
        {
            "Percentage": ["25%", "50%","75%"],
            "Timestamp": [final_values[0], final_values[1], final_values[2]],
        }
    )
    
    st.table(df)

st.set_page_config(layout='wide')
st.title("Time Calculator")

st.header("Part 1 - Provide time to transform")

time = st.text_area("Paste texts here", height=150)

percentages = [0.25,0.5,0.75]
# Add a button for the user to submit the URLs
if st.button("Transform"):
    
    if (input_validator(time)):
        transformation(time)

    