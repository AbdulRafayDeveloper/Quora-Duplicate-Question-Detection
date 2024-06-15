# Import necessary libraries
import streamlit as st
import pickle
from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import logging
import openai
import helper  # Import the helper module

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Load the machine learning model
model = pickle.load(open('model.pkl', 'rb'))

# Set page title and favicon
st.set_page_config(page_title="Question Answering App", page_icon=":question:", layout="wide")

# Custom CSS for dark theme
st.markdown("""
    <style>
        .main {
            background-color: #0e1117;
            color: white;
        }
        .stTextInput>div>div>input {
            background-color: #1f1f1f;
            color: white;
            border: 1px solid #444;
            padding: 10px;
            border-radius: 5px;
        }
        .stTextInput>div>label {
            color: white;
        }
        .stButton>button {
            background-color: #1f77b4;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-size: 16px;
        }
        .stButton>button:hover {
            background-color: #135a96;
        }
        .stSidebar {
            background-color: #222;
            color: white;
        }
        .stSidebar .stTextInput>div>div>input, .stSidebar .stTextInput>div>div>div {
            background-color: #444;
            color: white;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 5px;
        }
        .stSidebar .stButton>button {
            background-color: #1f77b4;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 5px;
            font-size: 14px;
        }
        .stSidebar .stButton>button:hover {
            background-color: #135a96;
        }
        .stAlert, .stTable {
            background-color: #1f1f1f;
            color: white;
            border: 1px solid #444;
            border-radius: 5px;
        }
        h1,p,h2,h3 {
            color: white;
        }
    </style>
""", unsafe_allow_html=True)

# Database configuration
DB_USER = 'root'
DB_PASSWORD = ''  # Add your password here
DB_HOST = 'localhost'
DB_NAME = 'duplicate'
DATABASE_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# Create the engine
engine = create_engine(DATABASE_URL)
Base = declarative_base()

# Define User and Question models
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password = Column(String(255), nullable=False)  # Store plain password

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    is_duplicate = Column(Boolean, nullable=False)
    answer = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship('User', back_populates='questions')

User.questions = relationship('Question', order_by=Question.id, back_populates='user')

# Create tables if they don't exist
Base.metadata.create_all(engine)

# Create a session factory
Session = sessionmaker(bind=engine)
session = Session()

# OpenAI API configuration
openai.api_key = ''  # Replace with your OpenAI API key

def generate_answer(question_text):
    try:
        response = openai.Completion.create(
            engine="gpt-3.5-turbo-instruct",  # Replace with the name of the new model
            prompt=question_text,
            max_tokens=150  # Adjust the number of tokens as needed
        )
        answer = response.choices[0].text.strip()
        return answer
    except Exception as e:
        logging.error(f"Error generating answer: {e}")
        return "An error occurred while generating the answer."

# Streamlit UI
def main():
    st.title("Question Answering App")
    
    menu = ["Home", "Login", "Register", "Questions", "Account"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    if choice == "Home":
        st.subheader("Home")
        st.write("Welcome to the Question Answering App!")
        
    elif choice in ["Login", "Register"]:
        st.subheader(f"{choice} Section")
        
        if choice == "Login":
            email = st.text_input("Email").strip().lower()
            password = st.text_input("Password", type='password')
            if st.button("Login"):
                user = session.query(User).filter_by(email=email).first()
                if user:
                    if password == user.password:
                        st.success(f"Welcome {user.username}")
                        st.session_state['user'] = user
                    else:
                        st.warning("Incorrect Password")
                else:
                    st.warning("Email does not exist")
        
        elif choice == "Register":
            new_username = st.text_input("Username")
            new_email = st.text_input("Email").strip().lower()
            new_password = st.text_input("Password", type='password')
            
            if st.button("Register"):
                if session.query(User).filter_by(username=new_username).first() or session.query(User).filter_by(email=new_email).first():
                    st.warning("Username or Email already exists")
                else:
                    new_user = User(username=new_username, email=new_email, password=new_password)
                    session.add(new_user)
                    session.commit()
                    st.success("You have successfully created a valid Account")
                    st.info("Go to Login Menu to login")
    
    elif choice == "Questions":
        if 'user' in st.session_state:
            st.subheader("Ask a Question")
            q1 = st.text_input('Enter question:')
            if st.button("Submit"):
                if not q1:
                    st.error("Please enter a question.")
                    return
                
                similar_questions = session.query(Question).all()
                duplicates = []
                
                for sq in similar_questions:
                    query = helper.query_point_creator(q1, sq.question_text)
                    result = model.predict(query)[0]
                    if result == 1:
                        duplicates.append(sq)

                if duplicates:
                    st.success('The question is similar to previously asked questions!')
                    st.subheader("Duplicate Questions Found")
                    for sq in duplicates:
                        st.write(f"**Question ID:** {sq.id}")
                        st.write(f"**Question:** {sq.question_text}")
                        st.write(f"**Asked by User ID:** {sq.user_id}")
                        st.write(f"**Answer:** {sq.answer}")
                        
                        st.write("---")
                    answer = duplicates[0].answer  # Use the answer from the first duplicate question
                else:
                    st.success('The question is not similar to any previously asked questions.')
                    answer = generate_answer(q1)
                    user_id = st.session_state['user'].id
                    new_question = Question(user_id=user_id, question_text=q1, is_duplicate=False, answer=answer)
                    session.add(new_question)
                    session.commit()
                    st.write("Question and answer saved successfully.")

                st.subheader("Answer:")
                st.write(answer)

            st.subheader("Your Questions")
            user_id = st.session_state['user'].id
            questions = session.query(Question).filter_by(user_id=user_id).all()
            
            # Display questions in a grid or card format
            cols = st.columns(2)
            for i, question in enumerate(questions):
                with cols[i % 2]:
                    st.write(f"**Question ID:** {question.id}")
                    st.write(f"**Question:** {question.question_text}")
                    st.write(f"**Duplicate:** {'Yes' if question.is_duplicate else 'No'}")
                    st.write(f"**Answer:** {question.answer}")
                    st.write(f"**Asked on:** {question.timestamp}")
                    st.write("---")
        else:
            st.warning("Please login to view and submit questions")
    
    elif choice == "Account":
        if 'user' in st.session_state:
            st.subheader("Account Details")
            user = st.session_state['user']
            st.write(f"**Username:** {user.username}")
            st.write(f"**Email:** {user.email}")
            
            st.subheader("Your Questions")
            questions = session.query(Question).filter_by(user_id=user.id).all()
            
            # Display questions in a grid or card format
            cols = st.columns(2)
            for i, question in enumerate(questions):
                with cols[i % 2]:
                    st.write(f"**Question ID:** {question.id}")
                    st.write(f"**Question:** {question.question_text}")
                    st.write(f"**Duplicate:** {'Yes' if question.is_duplicate else 'No'}")
                    st.write(f"**Answer:** {question.answer}")
                    st.write(f"**Asked on:** {question.timestamp}")
                    st.write("---")
        else:
            st.warning("Please login to view account details")

if __name__ == '__main__':
    main()
