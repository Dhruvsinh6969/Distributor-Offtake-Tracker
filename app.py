import streamlit as st
import pandas as pd
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ========== CONFIG ==========
st.set_page_config(page_title="Order Collection App", layout="centered")
os.makedirs("images", exist_ok=True)
GOOGLE_SHEET_ID = "1hbUt6Qzk_uMeYRX_1bV11JRwFyOpOXU8GutmzKe6TWU"
SERVICE_ACCOUNT_FILE = "streamlit-sheets.json"
DISTRIBUTOR_FILE = "distributors.csv"
PRODUCT_FILE = "products.csv"
USERS_FILE = "users.csv"
EMPLOYEE_MAPPING_FILE = "employee_distributor_map.csv"

# ========== GOOGLE AUTH ==========
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(GOOGLE_SHEET_ID).sheet1

drive_service = build('drive', 'v3', credentials=creds)
DRIVE_FOLDER_ID = "1b96TC89lrujL-JG66PZGhteTuQXSRVM0"

# ========== USER LOGIN ==========
ADMIN_CREDENTIALS = {"username": "admin", "password": "admin"}
USERS = {}

if os.path.exists(USERS_FILE):
    try:
        df_users = pd.read_csv(USERS_FILE)
        for _, row in df_users.iterrows():
            if row["Username"] != ADMIN_CREDENTIALS["username"]:
                USERS[row["Username"]] = {
                    "password": str(row["Password"]),
                    "role": row["Role"]
                }
    except Exception as e:
        st.error(f"Failed to load users file: {e}")
else:
    st.warning("User credentials file not found. Please upload it from admin panel.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
    st.session_state["username"] = ""
    st.session_state["role"] = ""

if not st.session_state["logged_in"]:
    st.title("\U0001F510 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_btn = st.button("Login")
    if login_btn:
        if username == ADMIN_CREDENTIALS["username"] and password == ADMIN_CREDENTIALS["password"]:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = "admin"
            st.success("Welcome Admin")
        elif username in USERS and USERS[username]["password"] == password:
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
            st.session_state["role"] = USERS[username]["role"]
            st.success(f"Welcome {username} ({st.session_state['role']})")
        else:
            st.error("Invalid username or password")
    st.stop()

# ========== ADMIN UPLOAD ==========
if st.session_state["role"] == "admin":
    st.sidebar.header("\U0001F4E4 Admin Panel")

    st.sidebar.markdown("Upload Distributors Excel (column: 'Distributor')")
    dist_file = st.sidebar.file_uploader("Distributors File", type=["xlsx", "csv"], key="dist")
    if dist_file:
        df = pd.read_excel(dist_file) if dist_file.name.endswith("xlsx") else pd.read_csv(dist_file)
        df.to_csv(DISTRIBUTOR_FILE, index=False)
        st.sidebar.success("Distributors updated.")

    st.sidebar.markdown("Upload Products Excel (column: 'Product')")
    prod_file = st.sidebar.file_uploader("Products File", type=["xlsx", "csv"], key="prod")
    if prod_file:
        df = pd.read_excel(prod_file) if prod_file.name.endswith("xlsx") else pd.read_csv(prod_file)
        df.to_csv(PRODUCT_FILE, index=False)
        st.sidebar.success("Products updated.")

    st.sidebar.markdown("Upload Users Excel (columns: 'Username', 'Password', 'Role')")
    users_file = st.sidebar.file_uploader("Users File", type=["xlsx", "csv"], key="users")
    if users_file:
        df = pd.read_excel(users_file) if users_file.name.endswith("xlsx") else pd.read_csv(users_file)
        df.to_csv(USERS_FILE, index=False)
        st.sidebar.success("User credentials updated. Please reload the app.")

    st.sidebar.markdown("Upload Employee Mapping File (columns: 'Employee', 'Distributor')")
    emp_map_file = st.sidebar.file_uploader("Employee Mapping File", type=["xlsx", "csv"], key="emp_map")
    if emp_map_file:
        df = pd.read_excel(emp_map_file) if emp_map_file.name.endswith("xlsx") else pd.read_csv(emp_map_file)
        df.to_csv(EMPLOYEE_MAPPING_FILE, index=False)
        st.sidebar.success("Employee-distributor mapping updated.")
        st.sidebar.write("Mapping Preview:")
        st.sidebar.dataframe(df)

# ========== LOAD OPTIONS ==========
employee_names = []
emp_map = pd.DataFrame()
if os.path.exists(EMPLOYEE_MAPPING_FILE):
    try:
        emp_map = pd.read_csv(EMPLOYEE_MAPPING_FILE)
        employee_names = emp_map[emp_map["Employee"] == st.session_state["username"]]["Employee"].unique().tolist()
    except:
        pass

distributors = ["D1", "D2", "D3"]
products = ["Donut Cake", "Chocochip Muffin", "Banana Muffin", "Brownie"]

if os.path.exists(DISTRIBUTOR_FILE):
    try:
        distributors = pd.read_csv(DISTRIBUTOR_FILE)["Distributor"].dropna().unique().tolist()
    except:
        pass

if os.path.exists(PRODUCT_FILE):
    try:
        products = pd.read_csv(PRODUCT_FILE)["Product"].dropna().unique().tolist()
    except:
        pass

# ========== HELPER FUNCTIONS ==========
def upload_to_drive(file_path, filename):
    try:
        media = MediaFileUpload(file_path, mimetype='image/jpeg')
        file_metadata = {'name': filename, 'parents': [DRIVE_FOLDER_ID]}
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id,webViewLink').execute()
        return file.get('webViewLink', '')
    except Exception as e:
        st.error(f"Error uploading to Drive: {str(e)}")
        return ""

def clear_form_data():
    keys_to_clear = ['employee_name', 'shop_name_input', 'margin_input', 'beat_area_input', 'distributor_select', 'remarks_input', 'num_visits', 'last_visited']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    for product in products:
        for prefix in ["product_", "stock_"]:
            key = f"{prefix}{product.replace(' ', '_')}"
            if key in st.session_state:
                del st.session_state[key]

# ========== EMPLOYEE FORM ==========
if st.session_state["role"] == "employee":
    st.title("\U0001F4CB Order Collection Form")
    st.markdown("You can upload or take a photo using your phone camera.")

    with st.form("order_form"):
        st.subheader("\U0001F9D1 Employee Info")
        name = st.selectbox("Your Name", employee_names, key="employee_name")

        filtered_distributors = distributors
        if not emp_map.empty and name:
            filtered_distributors = emp_map[emp_map["Employee"] == name]["Distributor"].dropna().unique().tolist()

        st.subheader("\U0001F3EA Shop Details")
        order_date = st.date_input("\U0001F4C5 Order Date", value=datetime.date.today())
        last_visited_date = st.date_input("\U0001F4C5 Last Visited Date")
        num_visits = st.number_input("\U0001F501 Number of Visits", min_value=1, step=1)
        photo = st.file_uploader("\U0001F4F8 Upload / Take Shop Photo", type=["jpg", "jpeg", "png"])
        distributor = st.selectbox("Select Distributor", filtered_distributors, key="distributor_select")
        shop_name = st.text_input("Shop Name", key="shop_name_input")
        margin = st.number_input("Margin (%)", min_value=0.0, max_value=100.0, value=20.0, step=0.1, key="margin_input")
        beat_area = st.text_input("Beat Area", key="beat_area_input")

        st.markdown("### \U0001F9FE Enter Product Quantity and Stock on Hand")
        header_cols = st.columns([2, 1, 1])
        header_cols[0].markdown("**Product**")
        header_cols[1].markdown("**Quantity**")
        header_cols[2].markdown("**Stock on Hand**")

        order_details = {}
        stock_on_hand = {}

        for product in products:
            cols = st.columns([2, 1, 1])
            cols[0].write(product)

            qty_key = f"product_{product.replace(' ', '_')}"
            soh_key = f"stock_{product.replace(' ', '_')}"

            qty = cols[1].number_input("", min_value=0, step=1, key=qty_key)
            soh = cols[2].number_input("", min_value=0, step=1, key=soh_key)

            if qty > 0:
                order_details[product] = qty
                stock_on_hand[product] = soh

        st.subheader("\U0001F4DD Additional Information")
        remarks = st.text_area("Remarks (Optional)", key="remarks_input")

        submitted = st.form_submit_button("\u2705 Submit Order")

    if submitted:
        if not name or not shop_name or not photo:
            st.error("Please complete all required fields and upload a photo.")
        elif sum(order_details.values()) == 0 and all(v == 0 for v in stock_on_hand.values()) and not remarks.strip():
            st.error("If no quantity or stock is entered, remarks must be filled.")
        else:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            photo_filename = f"{shop_name.replace(' ', '_')}_{timestamp}.jpg"
            photo_path = os.path.join("images", photo_filename)
            with open(photo_path, "wb") as f:
                f.write(photo.read())

            drive_url = upload_to_drive(photo_path, photo_filename)

            if not order_details:
                sheet.append_row([
                    timestamp, str(order_date), name, distributor, shop_name,
                    margin, beat_area, "", "", "",
                    photo_path, drive_url, remarks, str(last_visited_date), num_visits
                ])
            else:
                for product, qty in order_details.items():
                    sheet.append_row([
                        timestamp, str(order_date), name, distributor, shop_name,
                        margin, beat_area, product, qty, stock_on_hand.get(product, 0),
                        photo_path, drive_url, remarks, str(last_visited_date), num_visits
                    ])

            st.success("\u2705 Order submitted and saved to Google Sheet!")
            st.success(f"\U0001F4F8 Photo uploaded to Google Drive: {drive_url}")
            st.image(Image.open(photo_path), use_column_width=True)
            st.info("Form data cleared. You can now enter data for another shop.")
            clear_form_data()
        