import streamlit as st
import openai
import helper
import pickle

model = pickle.load(open('model.pkl','rb'))

# Set OpenAI API key
openai.api_key = ""

# Set page title and favicon
st.set_page_config(page_title="Question Answering App", page_icon=":question:")

# Set page header
st.title('Question Answering App')

# Collect user input for two questions
q1 = st.text_input('Enter question 1:')
q2 = st.text_input('Enter question 2:')

# Add a horizontal rule for visual separation
st.markdown("---")

# Check if the user has clicked the "Find" button
if st.button('Find'):
    # Create a feature vector for the input questions
    query = helper.query_point_creator(q1, q2)
    # Predict if the questions are duplicates or not
    result = model.predict(query)[0]

    # Display result based on prediction
    if result:
        st.success('The questions are similar! :heavy_check_mark:')
    else:
        st.error('The questions are not similar! :x:')

    # Use OpenAI API to generate answer for the first question
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",  # Replace with the name of the new model
            prompt=q1,
            max_tokens=10  # Adjust the number of tokens as needed
        )
        answer = response.choices[0].text.strip()
        st.subheader("Answer:")
        st.write(answer)
    except Exception as e:
        st.error("An error occurred while generating the answer.")
        st.error(str(e))
