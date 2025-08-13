import streamlit as st
import pandas as pd
import os
import json
from datetime import datetime
import qrcode
from PIL import Image
from io import BytesIO
import base64

# Constants
DATA_DIR = "data"
CANDIDATES_FILE = os.path.join(DATA_DIR, "candidates.csv")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
QR_CODE_FILE = os.path.join(DATA_DIR, "qr_code.png")
LOGO_FILE = "logo1.png"
os.makedirs(DATA_DIR, exist_ok=True)

# Department descriptions and requirements
DEPARTMENT_INFO = {
    "ICT": {
        "description": "Information and Communication Technology roles including software development, IT support, and network administration.",
        "requirements": "Matric certificate required. Relevant IT certifications or degree/diploma advantageous."
    },
    "RETAIL": {
        "description": "Retail positions including sales associates, store managers, and visual merchandisers.",
        "requirements": "Matric certificate required. Retail experience preferred."
    },
    "VOCATIONAL": {
        "description": "Skilled trade positions including electricians, plumbers, and automotive technicians.",
        "requirements": "Matric certificate required. Trade certification or apprenticeship required."
    },
    "AGRICULTURE": {
        "description": "Agricultural roles including farm managers, agronomists, and agricultural technicians.",
        "requirements": "Matric certificate required. Agricultural qualifications or experience preferred."
    },
    "SALES AND HOSPITALITY": {
        "description": "Sales and hospitality roles including account managers, hotel staff, and event coordinators.",
        "requirements": "Matric certificate required. Customer service experience preferred."
    },
    "CALL CENTRE": {
        "description": "Call center positions including customer service representatives and technical support agents.",
        "requirements": "Matric certificate required. Excellent communication skills essential."
    }
}

def generate_qr_code():
    """Generate QR code for application URL"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data("http://your-application-url.com")
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(QR_CODE_FILE)

def show_qr_code():
    """Display QR code for application"""
    if os.path.exists(QR_CODE_FILE):
        st.sidebar.image(QR_CODE_FILE, caption="Scan to access application", width=200)
        with open(QR_CODE_FILE, "rb") as f:
            st.sidebar.download_button(
                label="Download QR Code",
                data=f,
                file_name="mock_interview_qr.png",
                mime="image/png"
            )

def display_logo():
    """Display the logo if it exists"""
    if os.path.exists(LOGO_FILE):
        st.image(LOGO_FILE, width=200)
    else:
        st.warning("Logo image not found. Please ensure 'logo1.png' is in the same directory.")

def initialize_files():
    """Initialize data files and generate QR code if needed"""
    if not os.path.exists(CANDIDATES_FILE):
        pd.DataFrame(columns=[
            'timestamp', 'username', 'first_name', 'last_name', 'email', 'phone', 
            'department', 'position', 'cv_filename', 'status', 'room', 'notes'
        ]).to_csv(CANDIDATES_FILE, index=False)
    
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({
                "admin": {
                    "password": "candidate123",
                    "role": "candidate"
                },
                "facilitator": {
                    "password": "facilitator123",
                    "role": "facilitator"
                },
                "candidate": {
                    "password": "candidate123",
                    "role": "candidate"
                }
            }, f)

    if not os.path.exists(QR_CODE_FILE):
        generate_qr_code()

def set_custom_styles():
    """Set custom CSS styles for the entire application"""
    st.markdown("""
    <style>
    :root {
        --primary-color: #2c3e50;
        --secondary-color: #34495e;
        --accent-color: #3498db;
        --text-color: #333;
        --light-gray: #ecf0f1;
        --error-color: #e74c3c;
        --success-color: #2ecc71;
    }
    
    /* Main app styling */
    .stApp {
        background-color: #f5f7fa;
    }
    
    /* Login page specific styling */
    .login-container {
        max-width: 500px;
        margin: 2rem auto;
        padding: 2.5rem;
        border-radius: 10px;
        background: #FFFFFF;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border: 1px solid #E0E0E0;
    }
    
    .login-header {
        text-align: center;
        margin-bottom: 1.5rem;
        color: var(--primary-color);
        font-size: 2rem;
        font-weight: 600;
    }
    
    /* Form elements */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea,
    .stSelectbox>div>div>select {
        border: 1px solid #E0E0E0 !important;
        border-radius: 6px !important;
        padding: 10px !important;
    }
    
    .stButton>button {
        width: 100%;
        background-color: var(--primary-color) !important;
        color: white !important;
        font-weight: 500 !important;
        border: none !important;
        padding: 12px !important;
        border-radius: 6px !important;
        font-size: 1rem !important;
        transition: background-color 0.3s;
    }
    
    .stButton>button:hover {
        background-color: var(--secondary-color) !important;
    }
    
    /* Error messages */
    .error-message {
        color: var(--error-color) !important;
        font-weight: 500 !important;
        text-align: center !important;
        margin-top: 1rem !important;
    }
    
    /* Logo container */
    .logo-container {
        display: flex;
        justify-content: center;
        margin-bottom: 1.5rem;
    }
    
    /* Application form styling */
    .form-container {
        max-width: 800px;
        margin: 0 auto;
        padding: 2rem;
        border-radius: 10px;
        background: #FFFFFF;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border: 1px solid #E0E0E0;
    }
    
    .section-header {
        color: var(--primary-color);
        border-bottom: 1px solid #E0E0E0;
        padding-bottom: 0.5rem;
        margin-bottom: 1.5rem;
        font-weight: 600;
    }
    
    .department-card {
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        background: #F8F9FA;
        border-left: 4px solid var(--primary-color);
    }
    
    /* Dashboard cards */
    .applicant-card {
        padding: 1rem;
        margin-bottom: 1rem;
        border-radius: 8px;
        background: white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        border-left: 4px solid var(--primary-color);
    }
    
    /* Responsive adjustments */
    @media (max-width: 768px) {
        .login-container {
            padding: 1.5rem;
            margin: 1rem;
        }
        
        .form-container {
            padding: 1rem;
        }
        
        .section-header {
            font-size: 1.2rem;
        }
    }
    
    /* Password toggle button */
    .password-toggle-container {
        position: relative;
    }
    .password-toggle {
        position: absolute;
        right: 10px;
        top: 50%;
        transform: translateY(-50%);
        background: none;
        border: none;
        cursor: pointer;
        color: var(--secondary-color);
        font-size: 0.9rem;
    }
    </style>
    """, unsafe_allow_html=True)

def authenticate():
    """Handle user authentication with enhanced UI"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'show_password' not in st.session_state:
        st.session_state.show_password = False
    
    if not st.session_state.authenticated:
        set_custom_styles()
        
        # Login container with logo
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        
        # Logo display
        st.markdown('<div class="logo-container">', unsafe_allow_html=True)
        display_logo()
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Header
        st.markdown('<h1 class="login-header">MOCK INTERVIEW PLATFORM</h1>', unsafe_allow_html=True)
        
        # Login form
        with st.form("login_form"):
            username = st.text_input("Username", key="username_input")
            
            # Custom password input with toggle
            password_col = st.columns([1])[0]
            with password_col:
                password_type = "text" if st.session_state.show_password else "password"
                password = st.text_input("Password", type=password_type, key="password_input")
                
                # Toggle button using markdown and session state
                toggle_text = "Hide" if st.session_state.show_password else "Show"
                st.markdown(
                    f'<button class="password-toggle" type="button" onclick="window.togglePassword()">{toggle_text}</button>',
                    unsafe_allow_html=True
                )
            
            remember_me = st.checkbox("Remember me", value=True)
            
            submitted = st.form_submit_button("Login")
            
            if submitted:
                try:
                    with open(USERS_FILE, "r") as f:
                        users = json.load(f)
                    
                    if username in users:
                        if users[username]["password"] == password:
                            st.session_state.authenticated = True
                            st.session_state.role = users[username]["role"]
                            st.session_state.username = username
                            st.rerun()
                        else:
                            st.markdown('<p class="error-message">Invalid password</p>', unsafe_allow_html=True)
                    else:
                        st.markdown('<p class="error-message">Username not found</p>', unsafe_allow_html=True)
                except Exception as e:
                    st.markdown(f'<p class="error-message">Login error: {str(e)}</p>', unsafe_allow_html=True)
        
        # Forgot password link
        st.markdown('<div style="text-align: center; margin-top: 1rem;">', unsafe_allow_html=True)
        st.markdown('<a href="#" style="color: var(--secondary-color); text-decoration: none;">Forgot password?</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # JavaScript for password toggle
        st.markdown("""
        <script>
        window.togglePassword = function() {
            const passwordInput = document.querySelector('input[type="password"], input[type="text"]');
            if (passwordInput.type === "password") {
                passwordInput.type = "text";
                document.querySelector('.password-toggle').textContent = "Hide";
            } else {
                passwordInput.type = "password";
                document.querySelector('.password-toggle').textContent = "Show";
            }
        }
        </script>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    return True

def candidate_application():
    """Enhanced candidate application form"""
    st.title("Job Application Form")
    show_qr_code()
    
    with st.form("application_form"):
        st.markdown('<div class="form-container">', unsafe_allow_html=True)
        st.markdown('<div class="section-header">Personal Information</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name *")
        with col2:
            last_name = st.text_input("Last Name *")
        
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email *")
        with col2:
            phone = st.text_input("Phone Number *")
        
        st.markdown('<div class="section-header">Application Details</div>', unsafe_allow_html=True)
        
        department = st.selectbox(
            "Select Department *",
            ["", *DEPARTMENT_INFO.keys()],
            format_func=lambda x: "Select..." if x == "" else x
        )
        
        if department:
            with st.expander(f"ℹ️ {department} Department Information", expanded=True):
                st.markdown(f"""
                <div class="department-card">
                    <strong>Description:</strong> {DEPARTMENT_INFO[department]['description']}
                    <br><br>
                    <strong>Requirements:</strong> {DEPARTMENT_INFO[department]['requirements']}
                </div>
                """, unsafe_allow_html=True)
        
        position = st.text_input("Position Applying For *")
        room = st.selectbox(
            "Select Interview Room *",
            ["", "room2", "room3"],
            format_func=lambda x: "Select..." if x == "" else x.upper()
        )
        
        st.markdown('<div class="section-header">Upload Your CV</div>', unsafe_allow_html=True)
        cv_file = st.file_uploader("Upload CV (PDF or DOCX) *", type=["pdf", "docx"])
        
        submitted = st.form_submit_button("Submit Application")
        
        if submitted:
            if not all([first_name, last_name, email, phone, department, position, room, cv_file]):
                st.error("Please fill in all required fields (*)")
            else:
                try:
                    # Save CV
                    cv_filename = f"cv_{first_name}_{last_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{cv_file.name.split('.')[-1]}"
                    cv_path = os.path.join(DATA_DIR, cv_filename)
                    
                    with open(cv_path, "wb") as f:
                        f.write(cv_file.getbuffer())
                    
                    # Save application
                    new_application = {
                        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'username': st.session_state.username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'phone': phone,
                        'department': department,
                        'position': position,
                        'cv_filename': cv_filename,
                        'status': 'Submitted',
                        'room': room,
                        'notes': ''
                    }
                    
                    df = pd.read_csv(CANDIDATES_FILE)
                    df = pd.concat([df, pd.DataFrame([new_application])], ignore_index=True)
                    df.to_csv(CANDIDATES_FILE, index=False)
                    
                    st.success("Application submitted successfully!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Error submitting application: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_cv(cv_path):
    """Enhanced CV display with better error handling"""
    try:
        if cv_path.endswith('.pdf'):
            # For PDF files, show download button
            with open(cv_path, "rb") as f:
                cv_data = f.read()
            
            # Display PDF preview (works in some Streamlit deployments)
            base64_pdf = base64.b64encode(cv_data).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500" type="application/pdf">'
            st.markdown(pdf_display, unsafe_allow_html=True)
            
            st.download_button(
                label="Download PDF CV",
                data=cv_data,
                file_name=os.path.basename(cv_path),
                mime="application/pdf"
            )
        elif cv_path.endswith('.docx'):
            # For DOCX files, show download button
            with open(cv_path, "rb") as f:
                cv_data = f.read()
            st.download_button(
                label="Download DOCX CV",
                data=cv_data,
                file_name=os.path.basename(cv_path),
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.info("DOCX preview not available - please download to view")
        else:
            st.warning("Unsupported file format")
    except Exception as e:
        st.error(f"Error displaying CV: {str(e)}")

def facilitator_dashboard():
    """Enhanced facilitator dashboard"""
    st.title("Facilitator Dashboard")
    show_qr_code()
    
    # Room selection for facilitator
    room = st.sidebar.selectbox("Select Room to View", ["room2", "room3"])
    
    try:
        df = pd.read_csv(CANDIDATES_FILE)
    except Exception as e:
        st.error(f"Error loading applications: {str(e)}")
        df = pd.DataFrame()
    
    if df.empty:
        st.info("No applications submitted yet.")
        return
    
    # Filter by selected room
    df = df[df['room'] == room]
    
    if df.empty:
        st.info(f"No applications in {room.upper()} yet.")
        return
    
    # Filter options
    st.sidebar.header("Filters")
    department_filter = st.sidebar.selectbox(
        "Filter by Department",
        ["All"] + list(df['department'].unique()))
    
    status_filter = st.sidebar.selectbox(
        "Filter by Status",
        ["All"] + list(df['status'].unique()))
    
    # Apply filters
    if department_filter != "All":
        df = df[df['department'] == department_filter]
    
    if status_filter != "All":
        df = df[df['status'] == status_filter]
    
    # Display applications by department
    st.write(f"Showing {len(df)} applications in {room.upper()}")
    
    for department in df['department'].unique():
        dept_df = df[df['department'] == department]
        st.subheader(f"{department} Department ({len(dept_df)} applicants)")
        
        for _, row in dept_df.iterrows():
            with st.expander(f"{row['first_name']} {row['last_name']} - {row['position']} ({row['status']})", expanded=False):
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.markdown(f"""
                    <div class="applicant-card">
                        <p><strong>Name:</strong> {row['first_name']} {row['last_name']}</p>
                        <p><strong>Email:</strong> {row['email']}</p>
                        <p><strong>Phone:</strong> {row['phone']}</p>
                        <p><strong>Position:</strong> {row['position']}</p>
                        <p><strong>Room:</strong> {row['room'].upper()}</p>
                        <p><strong>Applied on:</strong> {row['timestamp']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    # CV viewing
                    cv_path = os.path.join(DATA_DIR, row['cv_filename'])
                    if os.path.exists(cv_path):
                        st.write("**CV:**")
                        display_cv(cv_path)
                    else:
                        st.warning("CV not found")
                    
                    # Status update form
                    with st.form(key=f"status_form_{row['timestamp']}"):
                        new_status = st.selectbox(
                            "Update Status",
                            ["Submitted", "Under Review", "Interview Scheduled", "Completed"],
                            index=["Submitted", "Under Review", "Interview Scheduled", "Completed"].index(row['status']),
                            key=f"status_{row['timestamp']}"
                        )
                        
                        notes = st.text_area(
                            "Add Notes",
                            value=row['notes'],
                            key=f"notes_{row['timestamp']}"
                        )
                        
                        if st.form_submit_button("Update"):
                            try:
                                df.loc[df['timestamp'] == row['timestamp'], 'status'] = new_status
                                df.loc[df['timestamp'] == row['timestamp'], 'notes'] = notes
                                df.to_csv(CANDIDATES_FILE, index=False)
                                st.success("Application updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating application: {str(e)}")

def admin_dashboard():
    """Enhanced admin dashboard"""
    st.title("Admin Dashboard")
    show_qr_code()
    
    try:
        df = pd.read_csv(CANDIDATES_FILE)
    except Exception as e:
        st.error(f"Error loading applications: {str(e)}")
        df = pd.DataFrame()
    
    if df.empty:
        st.info("No applications submitted yet.")
        return
    
    # Filter options
    st.sidebar.header("Filters")
    department_filter = st.sidebar.selectbox(
        "Filter by Department",
        ["All"] + list(df['department'].unique()))
    
    room_filter = st.sidebar.selectbox(
        "Filter by Room",
        ["All"] + list(df['room'].unique()))
    
    status_filter = st.sidebar.selectbox(
        "Filter by Status",
        ["All"] + list(df['status'].unique()))
    
    # Apply filters
    if department_filter != "All":
        df = df[df['department'] == department_filter]
    
    if room_filter != "All":
        df = df[df['room'] == room_filter]
    
    if status_filter != "All":
        df = df[df['status'] == status_filter]
    
    # Display all applications
    st.write(f"Showing {len(df)} applications")
    
    # Add export button
    if st.button("Export All Applications to CSV"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="all_applications.csv",
            mime="text/csv"
        )
    
    for department in df['department'].unique():
        dept_df = df[df['department'] == department]
        st.subheader(f"{department} Department ({len(dept_df)} applicants)")
        
        for room in dept_df['room'].unique():
            room_df = dept_df[dept_df['room'] == room]
            st.markdown(f"**{room.upper()}** ({len(room_df)} applicants)")
            
            for _, row in room_df.iterrows():
                with st.expander(f"{row['first_name']} {row['last_name']} - {row['position']} ({row['status']})", expanded=False):
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="applicant-card">
                            <p><strong>Name:</strong> {row['first_name']} {row['last_name']}</p>
                            <p><strong>Email:</strong> {row['email']}</p>
                            <p><strong>Phone:</strong> {row['phone']}</p>
                            <p><strong>Position:</strong> {row['position']}</p>
                            <p><strong>Room:</strong> {row['room'].upper()}</p>
                            <p><strong>Applied on:</strong> {row['timestamp']}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    with col2:
                        # CV viewing
                        cv_path = os.path.join(DATA_DIR, row['cv_filename'])
                        if os.path.exists(cv_path):
                            st.write("**CV:**")
                            display_cv(cv_path)
                        else:
                            st.warning("CV not found")
                        
                        st.write(f"**Status:** {row['status']}")
                        st.write(f"**Notes:** {row['notes']}")

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Mock Interview Platform",
        page_icon="💼",
        layout="wide"
    )
    
    # Apply custom styles
    set_custom_styles()
    
    initialize_files()
    
    if not authenticate():
        return
    
    # Navigation
    if st.session_state.role == "candidate":
        candidate_application()
    elif st.session_state.role == "facilitator":
        facilitator_dashboard()
    elif st.session_state.role == "admin":
        admin_dashboard()
    
    # Logout button
    if st.sidebar.button("🚪 Logout", key="logout_button"):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.session_state.username = None
        st.rerun()

if __name__ == "__main__":
    main()