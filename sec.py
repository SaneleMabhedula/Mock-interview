import streamlit as st
import pandas as pd
import json
from datetime import datetime
import os
from streamlit_lottie import st_lottie
import altair as alt
import numpy as np
from PIL import Image
import qrcode
import base64
from io import BytesIO
import hashlib
import shutil
from typing import Optional, Tuple
from streamlit.components.v1 import html
import platform

# Constants - using absolute paths for reliability
DATA_DIR = os.path.abspath("data")
SUBMISSIONS_FILE = os.path.join(DATA_DIR, "submissions.csv")
AUDIO_DIR = os.path.join(DATA_DIR, "audio")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
DELETED_ENTRIES_FILE = os.path.join(DATA_DIR, "deleted_entries.csv")

# Ensure directories exist with proper permissions
os.makedirs(DATA_DIR, exist_ok=True, mode=0o777)
os.makedirs(AUDIO_DIR, exist_ok=True, mode=0o777)
os.makedirs(BACKUP_DIR, exist_ok=True, mode=0o777)

# Define expected columns for submissions
EXPECTED_COLUMNS = [
    'timestamp', 'school', 'group_type', 'children_no', 'children_age',
    'adults_present', 'visit_date', 'programme', 'engagement', 'safety',
    'cleanliness', 'fun', 'learning', 'planning', 'safety_space',
    'comments', 'audio_file', 'device_type'
]

def initialize_data_files():
    """Initialize data files with proper structure and permissions"""
    try:
        # Initialize submissions file
        if not os.path.exists(SUBMISSIONS_FILE) or os.path.getsize(SUBMISSIONS_FILE) == 0:
            pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(SUBMISSIONS_FILE, index=False)
            os.chmod(SUBMISSIONS_FILE, 0o666)

        # Initialize deleted entries file
        if not os.path.exists(DELETED_ENTRIES_FILE) or os.path.getsize(DELETED_ENTRIES_FILE) == 0:
            pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(DELETED_ENTRIES_FILE, index=False)
            os.chmod(DELETED_ENTRIES_FILE, 0o666)

        # Initialize users file
        if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
            with open(USERS_FILE, "w") as f:
                json.dump({
                    "admin": {
                        "password": hashlib.sha256("Playafrica@2025!*".encode()).hexdigest(),
                        "role": "admin"
                    },
                    "Guest": {
                        "password": hashlib.sha256("Guest@2025".encode()).hexdigest(),
                        "role": "Guest"
                    }
                }, f)
            os.chmod(USERS_FILE, 0o666)
    except Exception as e:
        st.error(f"Initialization error: {str(e)}")

# Initialize data files at startup
initialize_data_files()

def audio_recorder():
    """Audio recorder component that works in Streamlit Cloud"""
    # Initialize session state for audio recording
    if 'audio_data' not in st.session_state:
        st.session_state.audio_data = None
    if 'audio_filename' not in st.session_state:
        st.session_state.audio_filename = None
    if 'recording_saved' not in st.session_state:
        st.session_state.recording_saved = False

    # Generate a unique key for this component instance
    component_key = f"audio_recorder_{id(st.session_state)}"
    
    # HTML and JavaScript for the audio recorder
    html_code = f"""
    <div id="audio-recorder-{component_key}" style="margin: 10px 0; font-family: Arial, sans-serif;">
        <button id="start-btn-{component_key}" onclick="startRecording_{component_key}()" 
                style="padding: 8px 16px; margin-right: 10px; background-color: #2E86AB; color: white; border: none; border-radius: 4px; cursor: pointer;">
            🎤 Start Recording
        </button>
        <button id="stop-btn-{component_key}" onclick="stopRecording_{component_key}()" 
                style="padding: 8px 16px; background-color: #F18F01; color: white; border: none; border-radius: 4px; cursor: pointer;" disabled>
            ⏹️ Stop Recording
        </button>
        <p id="status-{component_key}" style="margin-top: 10px; font-size: 14px; color: #555;">
            Ready to record (max 30 seconds)
        </p>
        <div id="preview-container-{component_key}" style="display: none; margin-top: 15px; padding: 10px; background-color: #f5f5f5; border-radius: 5px;">
            <p style="font-size: 14px; margin-bottom: 5px; font-weight: bold;">Your Recording:</p>
            <audio id="audio-preview-{component_key}" controls style="width: 100%;"></audio>
        </div>
    </div>

    <script>
    (function() {{
        let recorder_{component_key} = null;
        let audioChunks_{component_key} = [];
        let stream_{component_key} = null;
        
        window.startRecording_{component_key} = async function() {{
            try {{
                audioChunks_{component_key} = [];
                stream_{component_key} = await navigator.mediaDevices.getUserMedia({{ audio: true }});
                recorder_{component_key} = new MediaRecorder(stream_{component_key});
                
                recorder_{component_key}.ondataavailable = function(e) {{
                    if (e.data.size > 0) {{
                        audioChunks_{component_key}.push(e.data);
                    }}
                }};
                
                recorder_{component_key}.onstop = async function() {{
                    try {{
                        if (audioChunks_{component_key}.length === 0) {{
                            throw new Error("No audio data recorded");
                        }}
                        
                        const audioBlob = new Blob(audioChunks_{component_key}, {{ type: 'audio/wav' }});
                        const arrayBuffer = await audioBlob.arrayBuffer();
                        const base64Data = arrayBufferToBase64(arrayBuffer);
                        const filename = 'recording_' + new Date().getTime() + '.wav';
                        
                        // Create preview
                        const audioUrl = URL.createObjectURL(audioBlob);
                        document.getElementById('audio-preview-{component_key}').src = audioUrl;
                        document.getElementById('preview-container-{component_key}').style.display = 'block';
                        
                        // Send data to Streamlit
                        window.parent.postMessage({{
                            type: 'streamlit:setComponentValue',
                            value: {{
                                audio_data: base64Data,
                                filename: filename,
                                timestamp: new Date().getTime()
                            }}
                        }}, '*');
                        
                        document.getElementById('status-{component_key}').innerText = 'Recording complete - ready to submit';
                        document.getElementById('start-btn-{component_key}').disabled = false;
                        document.getElementById('stop-btn-{component_key}').disabled = true;
                        
                    }} catch (error) {{
                        console.error('Processing error:', error);
                        document.getElementById('status-{component_key}').innerText = 'Error processing recording';
                    }} finally {{
                        if (stream_{component_key}) {{
                            stream_{component_key}.getTracks().forEach(track => track.stop());
                        }}
                    }}
                }};
                
                recorder_{component_key}.start(100);
                document.getElementById('status-{component_key}').innerText = 'Recording... (Max 30 seconds)';
                document.getElementById('start-btn-{component_key}').disabled = true;
                document.getElementById('stop-btn-{component_key}').disabled = false;
                document.getElementById('preview-container-{component_key}').style.display = 'none';
                
                // Auto-stop after 30 seconds
                setTimeout(() => {{
                    if (recorder_{component_key} && recorder_{component_key}.state === 'recording') {{
                        recorder_{component_key}.stop();
                    }}
                }}, 30000);
                
            }} catch (error) {{
                console.error('Recording error:', error);
                document.getElementById('status-{component_key}').innerText = 'Error: ' + error.message;
            }}
        }};
        
        window.stopRecording_{component_key} = function() {{
            if (recorder_{component_key} && recorder_{component_key}.state === 'recording') {{
                recorder_{component_key}.stop();
            }}
        }};
        
        function arrayBufferToBase64(buffer) {{
            let binary = '';
            const bytes = new Uint8Array(buffer);
            for (let i = 0; i < bytes.byteLength; i++) {{
                binary += String.fromCharCode(bytes[i]);
            }}
            return window.btoa(binary);
        }}
    }})();
    </script>
    """
    
    # Render the component and get the returned value
    component_value = html(html_code, height=200)
    
    # Process the audio data if received
    if component_value and isinstance(component_value, dict):
        if 'audio_data' in component_value and component_value['audio_data']:
            try:
                # Decode and save the audio data
                audio_bytes = base64.b64decode(component_value['audio_data'])
                filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{component_value.get('timestamp', '')}.wav"
                audio_path = os.path.join(AUDIO_DIR, filename)
                
                # Ensure audio directory exists
                os.makedirs(AUDIO_DIR, exist_ok=True, mode=0o777)
                
                # Save the audio file
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                
                # Set proper permissions
                os.chmod(audio_path, 0o666)
                
                # Store in session state
                st.session_state.audio_data = audio_path
                st.session_state.audio_filename = filename
                st.session_state.recording_saved = True
                
                st.success("✅ Recording saved successfully!")
                
            except Exception as e:
                st.error(f"Error saving recording: {str(e)}")
                st.session_state.audio_data = None
                st.session_state.audio_filename = None
                st.session_state.recording_saved = False

def is_mobile():
    """Detect if user is on a mobile device"""
    try:
        user_agent = st.query_params.get("user_agent", [""])[0].lower()
        mobile_keywords = ['mobi', 'android', 'iphone', 'ipad', 'ipod']
        if any(keyword in user_agent for keyword in mobile_keywords):
            return True
        if st.query_params.get("screen_width", [""])[0]:
            screen_width = int(st.query_params.get("screen_width", ["768"])[0])
            return screen_width < 768
        return False
    except:
        return False

def responsive_columns(default_cols=2):
    """Create responsive columns based on device type"""
    if is_mobile():
        cols = []
        for i in range(default_cols):
            with st.container():
                cols.append(None)
        return cols
    return st.columns(default_cols)

def responsive_expander(label, expanded=True):
    """Create responsive expander based on device type"""
    if is_mobile():
        return st.expander(label, expanded=False)
    return st.expander(label, expanded=expanded)

def mobile_adjusted_text_input(label, value="", max_chars=None, key=None, placeholder=""):
    """Create responsive text input based on device type"""
    if is_mobile():
        return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)
    return st.text_input(label, value, max_chars=max_chars, key=key, placeholder=placeholder)

def mobile_adjusted_text_area(label, value="", height=100, key=None, placeholder=""):
    """Create responsive text area based on device type"""
    if is_mobile():
        return st.text_area(label, value, height=max(80, height//2), key=key, placeholder=placeholder)
    return st.text_area(label, value, height=height, key=key, placeholder=placeholder)

def create_backup() -> bool:
    """Create a backup of submissions with verification"""
    try:
        if not os.path.exists(SUBMISSIONS_FILE):
            return False
        
        os.makedirs(BACKUP_DIR, exist_ok=True, mode=0o777)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.csv")
        
        shutil.copy2(SUBMISSIONS_FILE, backup_path)
        os.chmod(backup_path, 0o666)
        
        # Verify backup was created
        if not os.path.exists(backup_path):
            raise Exception("Backup file not created")
        
        return True
    except Exception as e:
        st.error(f"Backup failed: {str(e)}")
        return False

def load_lottiefile(filepath: str) -> Optional[dict]:
    """Load Lottie animation file"""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading Lottie file: {str(e)}")
        return None

def save_submission(entry: dict) -> bool:
    """Save submission with proper validation and error handling"""
    try:
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in entry:
                entry[col] = None
        
        # Clean and validate data
        entry = {k: (v.strip() if isinstance(v, str) else v) for k, v in entry.items()}
        
        # Load existing data
        if os.path.exists(SUBMISSIONS_FILE) and os.path.getsize(SUBMISSIONS_FILE) > 0:
            existing_df = pd.read_csv(SUBMISSIONS_FILE)
            # Ensure all columns exist in the existing data
            for col in EXPECTED_COLUMNS:
                if col not in existing_df.columns:
                    existing_df[col] = None
        else:
            existing_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        # Create new DataFrame with the entry
        new_df = pd.DataFrame([entry])
        
        # Combine with existing data
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        
        # Save to file
        combined_df.to_csv(SUBMISSIONS_FILE, index=False)
        os.chmod(SUBMISSIONS_FILE, 0o666)  # Ensure proper permissions
        
        return True
    except Exception as e:
        st.error(f"Error saving submission: {str(e)}")
        return False

def load_submissions() -> pd.DataFrame:
    """Load submissions with robust error handling"""
    try:
        if not os.path.exists(SUBMISSIONS_FILE) or os.path.getsize(SUBMISSIONS_FILE) == 0:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        df = pd.read_csv(SUBMISSIONS_FILE)
        
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        # Validate audio file paths
        if 'audio_file' in df.columns:
            df['audio_file'] = df['audio_file'].apply(
                lambda x: x if isinstance(x, str) and os.path.exists(x) else None
            )
        
        return df
    except Exception as e:
        st.error(f"Error loading submissions: {str(e)}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def load_deleted_entries() -> pd.DataFrame:
    """Load deleted entries with validation"""
    try:
        if not os.path.exists(DELETED_ENTRIES_FILE) or os.path.getsize(DELETED_ENTRIES_FILE) == 0:
            return pd.DataFrame(columns=EXPECTED_COLUMNS)
        
        df = pd.read_csv(DELETED_ENTRIES_FILE)
        
        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None
        
        return df
    except Exception as e:
        st.error(f"Error loading deleted entries: {str(e)}")
        return pd.DataFrame(columns=EXPECTED_COLUMNS)

def delete_submission(index: int, permanent: bool = False) -> bool:
    """Delete submission with proper file handling"""
    try:
        df = load_submissions()
        
        if df.empty or index < 0 or index >= len(df):
            st.error("Invalid entry index or no data available")
            return False
        
        # Get the entry to be deleted
        entry_to_delete = df.iloc[index].copy()
        
        # Handle audio file cleanup
        audio_file = entry_to_delete.get('audio_file')
        if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
            if permanent:
                try:
                    os.remove(audio_file)
                except Exception as e:
                    st.warning(f"Could not delete audio file: {str(e)}")
        
        # Move to deleted entries if not permanent deletion
        if not permanent:
            try:
                deleted_df = load_deleted_entries()
                # Convert series to dataframe
                entry_df = pd.DataFrame([entry_to_delete])
                deleted_df = pd.concat([deleted_df, entry_df], ignore_index=True)
                deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
                os.chmod(DELETED_ENTRIES_FILE, 0o666)
            except Exception as e:
                st.error(f"Error moving to deleted entries: {str(e)}")
                return False
        
        # Remove from main submissions file
        df = df.drop(df.index[index]).reset_index(drop=True)
        df.to_csv(SUBMISSIONS_FILE, index=False)
        os.chmod(SUBMISSIONS_FILE, 0o666)
        
        # Force refresh
        st.rerun()
        return True
        
    except Exception as e:
        st.error(f"Deletion failed: {str(e)}")
        return False

def restore_deleted_entry(index: int) -> bool:
    """Restore a deleted entry"""
    try:
        deleted_df = load_deleted_entries()
        
        if deleted_df.empty or index < 0 or index >= len(deleted_df):
            st.error("Invalid entry index or no deleted entries available")
            return False
        
        # Get the entry to restore
        entry = deleted_df.iloc[index].to_dict()
        
        # Save to main submissions
        if save_submission(entry):
            # Remove from deleted entries
            deleted_df = deleted_df.drop(deleted_df.index[index]).reset_index(drop=True)
            deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
            os.chmod(DELETED_ENTRIES_FILE, 0o666)
            
            st.rerun()
            return True
        else:
            return False
            
    except Exception as e:
        st.error(f"Error restoring entry: {str(e)}")
        return False

def generate_qr_code(data: str) -> Tuple[str, Image.Image]:
    """Generate QR code from data"""
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        return base64.b64encode(img_bytes).decode(), img
    except Exception as e:
        st.error(f"Error generating QR code: {str(e)}")
        return "", None

def show_qr_code(data: str) -> None:
    """Display QR code with download option"""
    if not data:
        st.warning("No URL provided for QR code generation")
        return
    
    qr_img_base64, qr_img = generate_qr_code(data)
    if not qr_img_base64 or not qr_img:
        return
    
    st.markdown(f"""
    <div style="text-align: center; margin: 20px 0;">
        <img src="data:image/png;base64,{qr_img_base64}" width="200">
        <p style="font-size: 14px; margin-top: 10px;">
            Scan to access feedback form<br>
            Point your camera at the QR code
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.session_state.get('role') == 'admin':
        buffered = BytesIO()
        qr_img.save(buffered, format="PNG")
        img_bytes = buffered.getvalue()
        
        st.download_button(
            label="Download QR Code (Admin Only)",
            data=img_bytes,
            file_name="play_africa_feedback_qr.png",
            mime="image/png",
            help="Administrators can download this QR code for printing"
        )

def get_theme_colors() -> dict:
    """Get theme colors for consistent styling"""
    return {
        'text': 'var(--text-color)',
        'background': 'var(--background-color)',
        'card_bg': 'var(--card-bg-color)',
        'metric_value': 'var(--metric-value-color)',
        'metric_label': 'var(--metric-label-color)',
        'primary': '#2E86AB',
        'secondary': '#3FB0AC',
        'accent': '#F18F01'
    }

def show_confirmation_dialog(action: str, count: int) -> bool:
    """Show confirmation dialog for destructive actions"""
    with st.expander(f"⚠️ Confirm {action}", expanded=True):
        st.warning(f"You are about to {action.lower()} {count} feedback submission(s). This action cannot be undone.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ Confirm {action}", type="primary"):
                return True
        with col2:
            if st.button("❌ Cancel"):
                return False
    return False

def play_audio(filename: str) -> None:
    """Play audio with validation and download option"""
    try:
        if not filename or not isinstance(filename, str) or not os.path.exists(filename):
            st.warning("No valid audio file available")
            return
        
        # Verify it's a WAV file
        if not filename.lower().endswith('.wav'):
            st.error("Invalid audio format - only WAV files supported")
            return
        
        # Display audio player
        audio_bytes = open(filename, 'rb').read()
        st.audio(audio_bytes, format='audio/wav')
        
        # Add download button
        st.download_button(
            label="Download Recording",
            data=audio_bytes,
            file_name=os.path.basename(filename),
            mime="audio/wav",
            key=f"dl_{filename}"
        )
    except Exception as e:
        st.error(f"Error playing audio: {str(e)}")

def authenticate() -> bool:
    """Handle user authentication"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if not st.session_state.authenticated:
        try:
            moonkids_img = Image.open("play_africa_mag.jpg")
            paintingkids_img = Image.open("play2.jpg")
            moonkids_img = moonkids_img.resize((400, 300))
            paintingkids_img = paintingkids_img.resize((400, 300))
            
            def image_to_base64(img: Image.Image) -> str:
                buffered = BytesIO()
                img.save(buffered, format="JPEG")
                return base64.b64encode(buffered.getvalue()).decode()
            
            moonkids_base64 = image_to_base64(moonkids_img)
            paintingkids_base64 = image_to_base64(paintingkids_img)
            
        except FileNotFoundError as e:
            st.error(f"Image files not found: {str(e)}")
            return False
        except Exception as e:
            st.error(f"Error loading images: {str(e)}")
            return False

        st.markdown("""
        <style>
        .login-container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 20px;
        }
        .login-header {
            text-align: center;
            padding: 30px 0;
            margin-bottom: 30px;
            background: linear-gradient(135deg, #2E86AB, #3FB0AC);
            color: white;
            font-size: 42px;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 3px;
            border-radius: 12px;
            box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        }
        .login-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        .login-btn {
            background: linear-gradient(135deg, #2E86AB, #3FB0AC) !important;
            border: none !important;
            color: white !important;
            font-weight: bold !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            font-size: 16px !important;
        }
        .image-gallery {
            display: flex;
            justify-content: space-around;
            margin: 30px 0;
            flex-wrap: wrap;
        }
        .image-item {
            margin: 10px;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        @media (max-width: 768px) {
            .login-header {
                font-size: 24px;
                padding: 20px 0;
            }
            .image-gallery {
                flex-direction: column;
                align-items: center;
            }
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">🎪 Play Africa Feedback System</div>', unsafe_allow_html=True)
        
        # Image gallery
        st.markdown('<div class="image-gallery">', unsafe_allow_html=True)
        st.markdown(f'<div class="image-item"><img src="data:image/jpeg;base64,{moonkids_base64}" width="400"></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="image-item"><img src="data:image/jpeg;base64,{paintingkids_base64}" width="400"></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Login form
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown("### 🔐 Login to Continue")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", use_container_width=True)
            
            if login_button:
                try:
                    with open(USERS_FILE, "r") as f:
                        users = json.load(f)
                    
                    if username in users:
                        hashed_password = hashlib.sha256(password.encode()).hexdigest()
                        if users[username]["password"] == hashed_password:
                            st.session_state.authenticated = True
                            st.session_state.role = users[username]["role"]
                            st.session_state.username = username
                            st.success(f"Welcome, {username}!")
                            st.rerun()
                        else:
                            st.error("Invalid password")
                    else:
                        st.error("Username not found")
                except Exception as e:
                    st.error(f"Login error: {str(e)}")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Instructions
        st.markdown("""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 20px;">
            <h4>📋 System Information</h4>
            <p><strong>For Administrators:</strong> Use your admin credentials to access the full dashboard with analytics and management features.</p>
            <p><strong>For Guests:</strong> Use guest credentials to submit feedback only.</p>
            <p><strong>Need Help?</strong> Contact your system administrator for login credentials.</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        return False
    
    return True

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Play Africa Feedback System",
        page_icon="🎪",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
    .main-header {
        background: linear-gradient(135deg, #2E86AB, #3FB0AC);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-margin-bottom: 2rem;
    }
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2E86AB;
    }
    .stButton > button {
        width: 100%;
    }
    .feedback-form {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Authentication check
    if not authenticate():
        return
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🎪 Play Africa")
        st.markdown(f"**Welcome, {st.session_state.username}!**")
        st.markdown(f"**Role:** {st.session_state.role}")
        
        if st.session_state.role == 'admin':
            page = st.selectbox(
                "Navigate to:",
                ["📊 Dashboard", "📝 Submit Feedback", "🗂️ Manage Data", "🔄 Deleted Entries", "📱 QR Code"]
            )
        else:
            page = st.selectbox(
                "Navigate to:",
                ["📝 Submit Feedback", "📱 QR Code"]
            )
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.role = None
            st.session_state.username = None
            st.rerun()
    
    # Main content based on selected page
    if page == "📊 Dashboard" and st.session_state.role == 'admin':
        show_dashboard()
    elif page == "📝 Submit Feedback":
        show_feedback_form()
    elif page == "🗂️ Manage Data" and st.session_state.role == 'admin':
        show_data_management()
    elif page == "🔄 Deleted Entries" and st.session_state.role == 'admin':
        show_deleted_entries()
    elif page == "📱 QR Code":
        show_qr_page()

def show_dashboard():
    """Display admin dashboard with analytics"""
    st.markdown('<div class="main-header"><h1>📊 Play Africa Dashboard</h1></div>', unsafe_allow_html=True)
    
    df = load_submissions()
    
    if df.empty:
        st.info("No feedback submissions yet. Encourage visitors to submit feedback!")
        return
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Submissions", len(df))
    
    with col2:
        total_children = df['children_no'].fillna(0).astype(str).str.extract('(\d+)').astype(float).sum().iloc[0]
        st.metric("Total Children", int(total_children) if not pd.isna(total_children) else 0)
    
    with col3:
        avg_rating = df[['engagement', 'safety', 'cleanliness', 'fun', 'learning']].mean().mean()
        st.metric("Average Rating", f"{avg_rating:.1f}/5" if not pd.isna(avg_rating) else "N/A")
    
    with col4:
        audio_count = df['audio_file'].notna().sum()
        st.metric("Voice Recordings", audio_count)
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Ratings Distribution")
        rating_cols = ['engagement', 'safety', 'cleanliness', 'fun', 'learning']
        rating_data = df[rating_cols].melt(var_name='Category', value_name='Rating')
        rating_data = rating_data.dropna()
        
        if not rating_data.empty:
            chart = alt.Chart(rating_data).mark_bar().encode(
                x=alt.X('Category:N', title='Rating Category'),
                y=alt.Y('mean(Rating):Q', title='Average Rating', scale=alt.Scale(domain=[0, 5])),
                color=alt.Color('Category:N', scale=alt.Scale(scheme='viridis'))
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
    
    with col2:
        st.subheader("🏫 Submissions by School")
        school_counts = df['school'].value_counts().head(10)
        if not school_counts.empty:
            chart_data = pd.DataFrame({
                'School': school_counts.index,
                'Count': school_counts.values
            })
            chart = alt.Chart(chart_data).mark_bar().encode(
                x=alt.X('Count:Q', title='Number of Submissions'),
                y=alt.Y('School:N', sort='-x', title='School'),
                color=alt.value('#2E86AB')
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
    
    # Recent submissions
    st.subheader("📋 Recent Submissions")
    recent_df = df.head(10)[['timestamp', 'school', 'group_type', 'children_no', 'programme']]
    st.dataframe(recent_df, use_container_width=True)

def show_feedback_form():
    """Display feedback submission form"""
    st.markdown('<div class="main-header"><h1>📝 Submit Your Feedback</h1></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: #e8f4f8; padding: 1rem; border-radius: 8px; margin-bottom: 2rem;">
        <h4>🎪 Thank you for visiting Play Africa!</h4>
        <p>Your feedback helps us improve our programmes and create better experiences for children. 
        Please take a few minutes to share your thoughts.</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("feedback_form", clear_on_submit=True):
        st.markdown("### 📋 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            school = mobile_adjusted_text_input("School/Organization Name *", placeholder="Enter school or organization name")
            group_type = st.selectbox("Group Type *", ["", "School Group", "Community Group", "Family Visit", "Other"])
            children_no = mobile_adjusted_text_input("Number of Children *", placeholder="e.g., 25")
        
        with col2:
            children_age = mobile_adjusted_text_input("Age Range of Children *", placeholder="e.g., 6-12 years")
            adults_present = mobile_adjusted_text_input("Number of Adults Present", placeholder="e.g., 3")
            visit_date = st.date_input("Visit Date *", value=datetime.now().date())
        
        programme = st.selectbox(
            "Programme Attended *",
            ["", "Creative Arts Workshop", "Science Discovery", "Storytelling Session", "Music & Movement", "Drama Workshop", "Other"]
        )
        
        st.markdown("### ⭐ Rate Your Experience")
        st.markdown("*Please rate each aspect from 1 (Poor) to 5 (Excellent)*")
        
        col1, col2 = st.columns(2)
        with col1:
            engagement = st.select_slider("Children's Engagement Level", options=[1, 2, 3, 4, 5], value=3)
            safety = st.select_slider("Safety of Activities", options=[1, 2, 3, 4, 5], value=3)
            cleanliness = st.select_slider("Cleanliness of Facilities", options=[1, 2, 3, 4, 5], value=3)
        
        with col2:
            fun = st.select_slider("Fun Factor", options=[1, 2, 3, 4, 5], value=3)
            learning = st.select_slider("Educational Value", options=[1, 2, 3, 4, 5], value=3)
            planning = st.select_slider("Organization & Planning", options=[1, 2, 3, 4, 5], value=3)
        
        safety_space = st.radio(
            "Did you feel the space was safe for children? *",
            ["Yes, completely safe", "Mostly safe", "Some concerns", "Not safe"]
        )
        
        st.markdown("### 💭 Additional Comments")
        comments = mobile_adjusted_text_area(
            "Please share any additional thoughts, suggestions, or specific feedback:",
            height=120,
            placeholder="Tell us what you loved, what could be improved, or any suggestions you have..."
        )
        
        st.markdown("### 🎤 Voice Recording (Optional)")
        st.markdown("*Record a voice message to share your thoughts (max 30 seconds)*")
        
        # Initialize audio recording session state
        if 'audio_data' not in st.session_state:
            st.session_state.audio_data = None
        if 'recording_saved' not in st.session_state:
            st.session_state.recording_saved = False
        
        # Audio recorder component
        audio_recorder()
        
        # Show recording status
        if st.session_state.get('recording_saved', False):
            st.success("✅ Voice recording ready for submission!")
        
        # Device detection
        device_type = "Mobile" if is_mobile() else "Desktop"
        
        # Form submission
        submitted = st.form_submit_button("🚀 Submit Feedback", type="primary", use_container_width=True)
        
        if submitted:
            # Validation
            required_fields = {
                'School/Organization Name': school,
                'Group Type': group_type,
                'Number of Children': children_no,
                'Age Range': children_age,
                'Visit Date': visit_date,
                'Programme': programme,
                'Safety Assessment': safety_space
            }
            
            missing_fields = [field for field, value in required_fields.items() if not value]
            
            if missing_fields:
                st.error(f"Please fill in the following required fields: {', '.join(missing_fields)}")
            else:
                # Prepare submission data
                submission_data = {
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'school': school,
                    'group_type': group_type,
                    'children_no': children_no,
                    'children_age': children_age,
                    'adults_present': adults_present,
                    'visit_date': visit_date.strftime("%Y-%m-%d"),
                    'programme': programme,
                    'engagement': engagement,
                    'safety': safety,
                    'cleanliness': cleanliness,
                    'fun': fun,
                    'learning': learning,
                    'planning': planning,
                    'safety_space': safety_space,
                    'comments': comments,
                    'audio_file': st.session_state.get('audio_data', None),
                    'device_type': device_type
                }
                
                # Save submission
                if save_submission(submission_data):
                    st.success("🎉 Thank you! Your feedback has been submitted successfully!")
                    st.balloons()
                    
                    # Clear audio session state
                    st.session_state.audio_data = None
                    st.session_state.recording_saved = False
                    
                    # Show summary
                    with st.expander("📋 Submission Summary", expanded=True):
                        st.write(f"**School:** {school}")
                        st.write(f"**Programme:** {programme}")
                        st.write(f"**Children:** {children_no}")
                        st.write(f"**Overall Rating:** {(engagement + safety + cleanliness + fun + learning + planning) / 6:.1f}/5")
                        if st.session_state.get('audio_data'):
                            st.write("**Voice Recording:** ✅ Included")
                else:
                    st.error("❌ There was an error submitting your feedback. Please try again.")

def show_data_management():
    """Display data management interface for admins"""
    st.markdown('<div class="main-header"><h1>🗂️ Data Management</h1></div>', unsafe_allow_html=True)
    
    df = load_submissions()
    
    if df.empty:
        st.info("No submissions to manage yet.")
        return
    
    # Data overview
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Entries", len(df))
    with col2:
        audio_count = df['audio_file'].notna().sum()
        st.metric("With Audio", audio_count)
    with col3:
        if st.button("📥 Create Backup"):
            if create_backup():
                st.success("Backup created successfully!")
            else:
                st.error("Backup failed!")
    
    # Search and filter
    st.subheader("🔍 Search & Filter")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        search_school = st.text_input("Search by School", placeholder="Enter school name...")
    with col2:
        filter_programme = st.selectbox("Filter by Programme", ["All"] + df['programme'].dropna().unique().tolist())
    with col3:
        date_range = st.date_input("Filter by Date Range", value=[], help="Select start and end dates")
    
    # Apply filters
    filtered_df = df.copy()
    
    if search_school:
        filtered_df = filtered_df[filtered_df['school'].str.contains(search_school, case=False, na=False)]
    
    if filter_programme != "All":
        filtered_df = filtered_df[filtered_df['programme'] == filter_programme]
    
    if len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df['visit_date'] = pd.to_datetime(filtered_df['visit_date'])
        filtered_df = filtered_df[
            (filtered_df['visit_date'] >= pd.Timestamp(start_date)) &
            (filtered_df['visit_date'] <= pd.Timestamp(end_date))
        ]
    
    st.write(f"Showing {len(filtered_df)} of {len(df)} entries")
    
    # Data table with actions
    if not filtered_df.empty:
        for idx, row in filtered_df.iterrows():
            with st.expander(f"📋 {row['school']} - {row['programme']} ({row['timestamp']})", expanded=False):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.write(f"**School:** {row['school']}")
                    st.write(f"**Group Type:** {row['group_type']}")
                    st.write(f"**Children:** {row['children_no']} ({row['children_age']})")
                    st.write(f"**Programme:** {row['programme']}")
                    st.write(f"**Visit Date:** {row['visit_date']}")
                    
                    # Ratings
                    ratings = {
                        'Engagement': row['engagement'],
                        'Safety': row['safety'],
                        'Cleanliness': row['cleanliness'],
                        'Fun': row['fun'],
                        'Learning': row['learning'],
                        'Planning': row['planning']
                    }
                    
                    rating_cols = st.columns(3)
                    for i, (category, rating) in enumerate(ratings.items()):
                        with rating_cols[i % 3]:
                            st.metric(category, f"{rating}/5" if pd.notna(rating) else "N/A")
                    
                    if row['comments']:
                        st.write(f"**Comments:** {row['comments']}")
                    
                    # Audio playback
                    if row['audio_file'] and pd.notna(row['audio_file']):
                        st.write("**Voice Recording:**")
                        play_audio(row['audio_file'])
                    else:
                        st.write("**Voice Recording:** No recording available")
                
                with col2:
                    st.write("**Actions:**")
                    
                    # Find the actual index in the original dataframe
                    original_idx = df.index[df['timestamp'] == row['timestamp']].tolist()
                    if original_idx:
                        actual_idx = original_idx[0]
                        
                        if st.button(f"🗑️ Delete", key=f"del_{actual_idx}"):
                            if delete_submission(actual_idx, permanent=False):
                                st.success("Entry moved to deleted items!")
                        
                        if st.button(f"💥 Permanent Delete", key=f"perm_del_{actual_idx}"):
                            if show_confirmation_dialog("Permanent Delete", 1):
                                if delete_submission(actual_idx, permanent=True):
                                    st.success("Entry permanently deleted!")
    
    # Bulk actions
    if not filtered_df.empty:
        st.subheader("🔧 Bulk Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📊 Export Filtered Data"):
                csv = filtered_df.to_csv(index=False)
                st.download_button(
                    label="Download CSV",
                    data=csv,
                    file_name=f"play_africa_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("🗑️ Delete All Filtered"):
                if show_confirmation_dialog("Delete All Filtered", len(filtered_df)):
                    success_count = 0
                    for idx in filtered_df.index:
                        if delete_submission(idx, permanent=False):
                            success_count += 1
                    st.success(f"Moved {success_count} entries to deleted items!")

def show_deleted_entries():
    """Display and manage deleted entries"""
    st.markdown('<div class="main-header"><h1>🔄 Deleted Entries</h1></div>', unsafe_allow_html=True)
    
    deleted_df = load_deleted_entries()
    
    if deleted_df.empty:
        st.info("No deleted entries found.")
        return
    
    st.write(f"**Total Deleted Entries:** {len(deleted_df)}")
    
    # Display deleted entries
    for idx, row in deleted_df.iterrows():
        with st.expander(f"🗑️ {row['school']} - {row['programme']} (Deleted)", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**School:** {row['school']}")
                st.write(f"**Programme:** {row['programme']}")
                st.write(f"**Children:** {row['children_no']}")
                st.write(f"**Visit Date:** {row['visit_date']}")
                
                if row['comments']:
                    st.write(f"**Comments:** {row['comments']}")
                
                if row['audio_file'] and pd.notna(row['audio_file']):
                    st.write("**Voice Recording:**")
                    play_audio(row['audio_file'])
            
            with col2:
                st.write("**Actions:**")
                
                if st.button(f"↩️ Restore", key=f"restore_{idx}"):
                    if restore_deleted_entry(idx):
                        st.success("Entry restored successfully!")
                
                if st.button(f"💥 Permanent Delete", key=f"perm_del_deleted_{idx}"):
                    if show_confirmation_dialog("Permanent Delete", 1):
                        # Remove from deleted entries permanently
                        try:
                            # Handle audio file deletion
                            audio_file = row.get('audio_file')
                            if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                                try:
                                    os.remove(audio_file)
                                except Exception as e:
                                    st.warning(f"Could not delete audio file: {str(e)}")
                            
                            # Remove from deleted entries file
                            deleted_df = deleted_df.drop(deleted_df.index[idx]).reset_index(drop=True)
                            deleted_df.to_csv(DELETED_ENTRIES_FILE, index=False)
                            os.chmod(DELETED_ENTRIES_FILE, 0o666)
                            
                            st.success("Entry permanently deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error permanently deleting entry: {str(e)}")
    
    # Bulk actions for deleted entries
    if not deleted_df.empty:
        st.subheader("🔧 Bulk Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("↩️ Restore All"):
                if show_confirmation_dialog("Restore All", len(deleted_df)):
                    success_count = 0
                    for idx in range(len(deleted_df)):
                        if restore_deleted_entry(0):  # Always restore the first entry as indices shift
                            success_count += 1
                    st.success(f"Restored {success_count} entries!")
        
        with col2:
            if st.button("💥 Permanently Delete All"):
                if show_confirmation_dialog("Permanently Delete All", len(deleted_df)):
                    try:
                        # Delete all audio files
                        for _, row in deleted_df.iterrows():
                            audio_file = row.get('audio_file')
                            if audio_file and isinstance(audio_file, str) and os.path.exists(audio_file):
                                try:
                                    os.remove(audio_file)
                                except:
                                    pass
                        
                        # Clear the deleted entries file
                        pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(DELETED_ENTRIES_FILE, index=False)
                        os.chmod(DELETED_ENTRIES_FILE, 0o666)
                        
                        st.success("All deleted entries permanently removed!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing deleted entries: {str(e)}")

def show_qr_page():
    """Display QR code for easy access"""
    st.markdown('<div class="main-header"><h1>📱 QR Code Access</h1></div>', unsafe_allow_html=True)
    
    st.markdown("""
    <div style="background: #e8f4f8; padding: 1.5rem; border-radius: 8px; margin-bottom: 2rem;">
        <h4>📱 Easy Mobile Access</h4>
        <p>Use this QR code to provide quick access to the feedback form. Visitors can scan it with their phone cameras to instantly access the feedback system.</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Get current URL (you might need to adjust this based on your deployment)
    current_url = "https://your-streamlit-app-url.com"  # Replace with your actual URL
    
    # Generate and display QR code
    show_qr_code(current_url)
    
    st.markdown("""
    ### 📋 Instructions for Use:
    
    1. **Print the QR Code**: Download and print the QR code to display at your venue
    2. **Mobile Access**: Visitors can scan the code with their phone camera
    3. **Instant Access**: The code opens the feedback form directly in their browser
    4. **No App Required**: Works with any smartphone camera or QR code reader
    
    ### 💡 Tips:
    - Place QR codes at exit points for maximum visibility
    - Include a brief instruction like "Scan to share your feedback"
    - Test the QR code before printing to ensure it works correctly
    """)

if __name__ == "__main__":
    main()