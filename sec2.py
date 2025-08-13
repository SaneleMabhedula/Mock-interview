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
    component_key = f"audio_recorder_{hash(str(st.session_state))}"

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
            padding: 12px 30px !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            text-transform: uppercase !important;
            letter-spacing: 1px !important;
            transition: all 0.3s ease !important;
        }
        .login-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
        }
        .image-gallery {
            display: flex;
            justify-content: center;
            gap: 20px;
            margin: 30px 0;
            flex-wrap: wrap;
        }
        .image-item {
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 20px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .image-item:hover {
            transform: scale(1.05);
        }
        .welcome-text {
            text-align: center;
            font-size: 18px;
            color: #333;
            margin: 20px 0;
            line-height: 1.6;
        }
        </style>
        """, unsafe_allow_html=True)

        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.markdown('<div class="login-header">🎮 Play Africa Feedback System</div>', unsafe_allow_html=True)

        # Image gallery
        st.markdown(f"""
        <div class="image-gallery">
            <div class="image-item">
                <img src="data:image/jpeg;base64,{moonkids_base64}" width="400" height="300">
            </div>
            <div class="image-item">
                <img src="data:image/jpeg;base64,{paintingkids_base64}" width="400" height="300">
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div class="welcome-text">
            Welcome to the Play Africa Feedback System! 🌟<br>
            Share your experience and help us create better play experiences for children across Africa.
        </div>
        """, unsafe_allow_html=True)

        # Login form
        with st.container():
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.markdown("### 🔐 Login to Continue")
                
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                
                if st.button("🚀 Login", key="login_btn"):
                    if username and password:
                        try:
                            with open(USERS_FILE, "r") as f:
                                users = json.load(f)
                            
                            if username in users:
                                hashed_password = hashlib.sha256(password.encode()).hexdigest()
                                if users[username]["password"] == hashed_password:
                                    st.session_state.authenticated = True
                                    st.session_state.username = username
                                    st.session_state.role = users[username]["role"]
                                    st.success(f"Welcome, {username}!")
                                    st.rerun()
                                else:
                                    st.error("❌ Invalid password")
                            else:
                                st.error("❌ Username not found")
                        except Exception as e:
                            st.error(f"Login error: {str(e)}")
                    else:
                        st.warning("⚠️ Please enter both username and password")

            st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
        return False

    return True

def feedback_form():
    """Main feedback form"""
    st.markdown("""
    <style>
    .form-header {
        background: linear-gradient(135deg, #2E86AB, #3FB0AC);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
    }
    .form-section {
        background: #f8f9fa;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        border-left: 4px solid #2E86AB;
    }
    .submit-btn {
        background: linear-gradient(135deg, #2E86AB, #3FB0AC) !important;
        color: white !important;
        border: none !important;
        padding: 15px 30px !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 16px !important;
                width: 100% !important;
        margin-top: 20px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="form-header"><h1>🎮 Play Africa Feedback Form</h1><p>Help us improve play experiences for children!</p></div>', unsafe_allow_html=True)

    with st.form("feedback_form", clear_on_submit=True):
        # Basic Information Section
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### 📋 Basic Information")
        
        col1, col2 = st.columns(2)
        with col1:
            school = mobile_adjusted_text_input("School/Organization Name *", placeholder="Enter school name")
            group_type = st.selectbox("Group Type *", ["", "School Group", "Community Group", "Family Group", "Other"])
            children_no = st.number_input("Number of Children *", min_value=1, max_value=100, value=1)
        
        with col2:
            children_age = st.selectbox("Children's Age Range *", ["", "3-5 years", "6-8 years", "9-12 years", "13-15 years", "Mixed ages"])
            adults_present = st.number_input("Number of Adults Present *", min_value=1, max_value=20, value=1)
            visit_date = st.date_input("Visit Date *", value=datetime.now().date())
        
        programme = st.selectbox("Programme Attended *", ["", "Creative Play", "Sports & Games", "Educational Activities", "Arts & Crafts", "Music & Dance", "Other"])
        st.markdown('</div>', unsafe_allow_html=True)

        # Rating Section
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### ⭐ Rate Your Experience (1 = Poor, 5 = Excellent)")
        
        col1, col2 = st.columns(2)
        with col1:
            engagement = st.slider("How engaged were the children?", 1, 5, 3)
            safety = st.slider("How safe did you feel the environment was?", 1, 5, 3)
            cleanliness = st.slider("How clean were the facilities?", 1, 5, 3)
        
        with col2:
            fun = st.slider("How much fun did the children have?", 1, 5, 3)
            learning = st.slider("How much did the children learn?", 1, 5, 3)
            planning = st.slider("How well-planned were the activities?", 1, 5, 3)
        
        safety_space = st.slider("Overall, how would you rate the safety of the play space?", 1, 5, 3)
        st.markdown('</div>', unsafe_allow_html=True)

        # Comments and Audio Section
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("### 💬 Additional Feedback")
        
        comments = mobile_adjusted_text_area(
            "Additional Comments", 
            placeholder="Share any additional thoughts, suggestions, or experiences...",
            height=120
        )
        
        st.markdown("#### 🎤 Voice Recording (Optional)")
        st.markdown("Record a voice message to share your thoughts:")
        
        # Audio recorder
        audio_recorder()
        
        # Show recording status
        if st.session_state.get('recording_saved', False):
            st.success("✅ Voice recording ready for submission!")
            if st.session_state.get('audio_data'):
                st.audio(open(st.session_state.audio_data, 'rb').read(), format='audio/wav')
        
        st.markdown('</div>', unsafe_allow_html=True)

        # Submit button
        submitted = st.form_submit_button("🚀 Submit Feedback", help="Click to submit your feedback")

        if submitted:
            # Validation
            required_fields = [school, group_type, children_no, children_age, adults_present, visit_date, programme]
            if not all(required_fields):
                st.error("❌ Please fill in all required fields marked with *")
                return

            try:
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
                    'device_type': 'Mobile' if is_mobile() else 'Desktop'
                }

                # Save submission
                if save_submission(submission_data):
                    st.success("🎉 Thank you! Your feedback has been submitted successfully!")
                    
                    # Clear audio session state
                    st.session_state.audio_data = None
                    st.session_state.audio_filename = None
                    st.session_state.recording_saved = False
                    
                    # Show success message with animation
                    st.balloons()
                    
                    # Option to submit another feedback
                    if st.button("📝 Submit Another Feedback"):
                        st.rerun()
                else:
                    st.error("❌ Failed to submit feedback. Please try again.")
                    
            except Exception as e:
                st.error(f"❌ Error submitting feedback: {str(e)}")

def admin_dashboard():
    """Admin dashboard for viewing and managing submissions"""
    st.markdown("""
    <style>
    .admin-header {
        background: linear-gradient(135deg, #2E86AB, #3FB0AC);
        color: white;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        text-align: center;
        border-left: 4px solid #2E86AB;
    }
    .delete-btn {
        background-color: #dc3545 !important;
        color: white !important;
        border: none !important;
        padding: 5px 10px !important;
        border-radius: 4px !important;
        font-size: 12px !important;
    }
    .permanent-delete-btn {
        background-color: #6f42c1 !important;
        color: white !important;
        border: none !important;
        padding: 5px 10px !important;
        border-radius: 4px !important;
        font-size: 12px !important;
    }
    .restore-btn {
        background-color: #28a745 !important;
        color: white !important;
        border: none !important;
        padding: 5px 10px !important;
        border-radius: 4px !important;
        font-size: 12px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="admin-header"><h1>🛠️ Admin Dashboard</h1><p>Manage feedback submissions and view analytics</p></div>', unsafe_allow_html=True)

    # Load data
    df = load_submissions()
    deleted_df = load_deleted_entries()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Total Submissions", len(df))
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        avg_rating = df[['engagement', 'safety', 'cleanliness', 'fun', 'learning', 'planning', 'safety_space']].mean().mean() if not df.empty else 0
        st.metric("Average Rating", f"{avg_rating:.1f}/5")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        audio_count = df['audio_file'].notna().sum() if not df.empty else 0
        st.metric("Voice Recordings", audio_count)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col4:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("Deleted Entries", len(deleted_df))
        st.markdown('</div>', unsafe_allow_html=True)

    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Active Submissions", "🗑️ Deleted Entries", "📈 Analytics", "⚙️ Settings"])

    with tab1:
        st.markdown("### 📋 Active Feedback Submissions")
        
        if df.empty:
            st.info("No submissions found.")
        else:
            # Bulk actions
            st.markdown("#### Bulk Actions")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Delete All Submissions"):
                    if show_confirmation_dialog("Delete All", len(df)):
                        for i in range(len(df)):
                            delete_submission(0, permanent=False)
                        st.success("All submissions moved to deleted entries")
                        st.rerun()
            
            with col2:
                if st.button("💾 Create Backup"):
                    if create_backup():
                        st.success("Backup created successfully!")
                    else:
                        st.error("Failed to create backup")
            
            with col3:
                if st.button("📥 Download CSV"):
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download Data",
                        data=csv,
                        file_name=f"feedback_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )

            # Display submissions
            for i, row in df.iterrows():
                with st.expander(f"📝 {row['school']} - {row['timestamp']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**School:** {row['school']}")
                        st.write(f"**Group Type:** {row['group_type']}")
                        st.write(f"**Children:** {row['children_no']} ({row['children_age']})")
                        st.write(f"**Adults:** {row['adults_present']}")
                        st.write(f"**Programme:** {row['programme']}")
                        st.write(f"**Visit Date:** {row['visit_date']}")
                    
                    with col2:
                        st.write("**Ratings:**")
                        ratings = {
                            'Engagement': row['engagement'],
                            'Safety': row['safety'],
                            'Cleanliness': row['cleanliness'],
                            'Fun': row['fun'],
                            'Learning': row['learning'],
                            'Planning': row['planning'],
                            'Safety Space': row['safety_space']
                        }
                        for rating_name, rating_value in ratings.items():
                            st.write(f"- {rating_name}: {'⭐' * int(rating_value)} ({rating_value}/5)")
                    
                    if row['comments']:
                        st.write(f"**Comments:** {row['comments']}")
                    
                    # Audio playback
                    if row['audio_file'] and pd.notna(row['audio_file']):
                        st.write("**Voice Recording:**")
                        play_audio(row['audio_file'])
                    
                    # Action buttons
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if st.button(f"🗑️ Delete", key=f"delete_{i}"):
                            if delete_submission(i, permanent=False):
                                st.success("Entry moved to deleted items")
                                st.rerun()
                    
                    with col2:
                        if st.button(f"💀 Permanent Delete", key=f"perm_delete_{i}"):
                            if show_confirmation_dialog("Permanently Delete", 1):
                                if delete_submission(i, permanent=True):
                                    st.success("Entry permanently deleted")
                                    st.rerun()

    with tab2:
        st.markdown("### 🗑️ Deleted Entries")
        
        if deleted_df.empty:
            st.info("No deleted entries found.")
        else:
            st.warning(f"Found {len(deleted_df)} deleted entries")
            
            # Bulk restore
            if st.button("↩️ Restore All Deleted Entries"):
                if show_confirmation_dialog("Restore All", len(deleted_df)):
                    for i in range(len(deleted_df)):
                        restore_deleted_entry(0)
                    st.success("All entries restored")
                    st.rerun()
            
            # Display deleted entries
            for i, row in deleted_df.iterrows():
                with st.expander(f"🗑️ {row['school']} - {row['timestamp']}", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**School:** {row['school']}")
                        st.write(f"**Group Type:** {row['group_type']}")
                        st.write(f"**Children:** {row['children_no']} ({row['children_age']})")
                        st.write(f"**Programme:** {row['programme']}")
                    
                    with col2:
                        avg_rating = np.mean([row['engagement'], row['safety'], row['cleanliness'], 
                                           row['fun'], row['learning'], row['planning'], row['safety_space']])
                        st.write(f"**Average Rating:** {avg_rating:.1f}/5")
                        st.write(f"**Visit Date:** {row['visit_date']}")
                    
                    if row['comments']:
                        st.write(f"**Comments:** {row['comments']}")
                    
                    # Audio playback for deleted entries
                    if row['audio_file'] and pd.notna(row['audio_file']):
                        st.write("**Voice Recording:**")
                        play_audio(row['audio_file'])
                    
                    # Restore button
                    if st.button(f"↩️ Restore", key=f"restore_{i}"):
                        if restore_deleted_entry(i):
                            st.success("Entry restored successfully")
                            st.rerun()

    with tab3:
        st.markdown("### 📈 Analytics Dashboard")
        
        if df.empty:
            st.info("No data available for analytics.")
        else:
            # Rating distribution
            st.markdown("#### Rating Distribution")
            rating_cols = ['engagement', 'safety', 'cleanliness', 'fun', 'learning', 'planning', 'safety_space']
            rating_data = df[rating_cols].melt(var_name='Category', value_name='Rating')
            
            chart = alt.Chart(rating_data).mark_bar().encode(
                x=alt.X('Category:N', title='Rating Category'),
                y=alt.Y('mean(Rating):Q', title='Average Rating'),
                color=alt.Color('Category:N', scale=alt.Scale(scheme='category10'))
            ).properties(width=600, height=400)
            
            st.altair_chart(chart, use_container_width=True)
            
            # Programme popularity
            st.markdown("#### Programme Popularity")
            programme_counts = df['programme'].value_counts()
            
            chart2 = alt.Chart(programme_counts.reset_index()).mark_arc().encode(
                theta=alt.Theta('count:Q'),
                color=alt.Color('programme:N'),
                tooltip=['programme:N', 'count:Q']
            ).properties(width=400, height=400)
            
            st.altair_chart(chart2, use_container_width=True)
            
            # Submissions over time
            st.markdown("#### Submissions Over Time")
            df['date'] = pd.to_datetime(df['timestamp']).dt.date
            daily_counts = df.groupby('date').size().reset_index(name='count')
            
            chart3 = alt.Chart(daily_counts).mark_line(point=True).encode(
                x=alt.X('date:T', title='Date'),
                y=alt.Y('count:Q', title='Number of Submissions'),
                tooltip=['date:T', 'count:Q']
            ).properties(width=600, height=300)
            
            st.altair_chart(chart3, use_container_width=True)

    with tab4:
        st.markdown("### ⚙️ System Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔧 Data Management")
            
            if st.button("🗑️ Clear All Data"):
                if show_confirmation_dialog("Clear All Data", len(df) + len(deleted_df)):
                    try:
                        # Clear submissions
                        pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(SUBMISSIONS_FILE, index=False)
                        # Clear deleted entries
                        pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(DELETED_ENTRIES_FILE, index=False)
                        # Clear audio files
                        for file in os.listdir(AUDIO_DIR):
                            if file.endswith('.wav'):
                                os.remove(os.path.join(AUDIO_DIR, file))
                        st.success("All data cleared successfully")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error clearing data: {str(e)}")
            
            if st.button("💾 Export All Data"):
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Create export package
                    export_data = {
                        'active_submissions': df.to_dict('records'),
                        'deleted_entries': deleted_df.to_dict('records'),
                        'export_timestamp': timestamp,
                        'total_submissions': len(df),
                        'total_deleted': len(deleted_df)
                    }
                    
                    export_json = json.dumps(export_data, indent=2, default=str)
                    
                    st.download_button(
                        label="Download Complete Export",
                        data=export_json,
                        file_name=f"play_africa_export_{timestamp}.json",
                        mime="application/json"
                    )
                except Exception as e:
                    st.error(f"Export failed: {str(e)}")
        
        with col2:
            st.markdown("#### 📱 QR Code Generator")
            
            # Get current URL for QR code
            try:
                current_url = st.query_params.get("url", ["https://your-app-url.streamlit.app"])[0]
            except:
                current_url = "https://your-app-url.streamlit.app"
            
            custom_url = st.text_input("Custom URL for QR Code", value=current_url)
            
            if custom_url:
                show_qr_code(custom_url)

def main():
    """Main application function"""
    # Set page config
    st.set_page_config(
        page_title="Play Africa Feedback System",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    # Custom CSS for mobile responsiveness
    st.markdown("""
    <style>
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stButton > button {
            width: 100%;
        }
        .stSelectbox > div > div {
            font-size: 14px;
        }
        .stTextInput > div > div > input {
            font-size: 14px;
        }
    }
    
    .stApp > header {
        background-color: transparent;
    }
    
    .stApp {
        margin-top: -80px;
    }
    
    .main-header {
        background: linear-gradient(135deg, #2E86AB, #3FB0AC);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # Authentication
    if not authenticate():
        return

    # Sidebar for navigation
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.username}!")
        st.markdown(f"**Role:** {st.session_state.role}")
        
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.role = None
            st.rerun()

    # Main content based on role
    if st.session_state.role == "admin":
        # Admin can access both feedback form and dashboard
        page = st.sidebar.selectbox("Select Page", ["📝 Feedback Form", "🛠️ Admin Dashboard"])
        
        if page == "📝 Feedback Form":
            feedback_form()
        else:
            admin_dashboard()
    else:
        # Regular users only see feedback form
        feedback_form()

if __name__ == "__main__":
    main()

