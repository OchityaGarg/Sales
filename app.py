import streamlit as st
from pymongo import MongoClient
import hashlib

# ----------------------------
# MongoDB Connection
# ----------------------------
client = MongoClient(st.secrets["mongodb"]["uri"])
db = client[st.secrets["mongodb"]["database"]]
users_col = db["users"]
products_col = db["products"]
orders_col = db["orders"]

# ----------------------------
# Helper Functions
# ----------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

def login_user(username, password):
    """Authenticate admin or user."""
    if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
        return "admin"
    user = users_col.find_one({"username": username, "password": hash_password(password)})
    if user:
        return "user"
    return None

# ----------------------------
# Admin Dashboard
# ----------------------------
def admin_dashboard():
    st.title("🛒 Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["👤 Create User", "📦 Add Product", "📋 View Data"])

    # Create User
    with tab1:
        st.subheader("Create User")
        new_user = st.text_input("New Username", key="new_user")
        new_pass = st.text_input("New Password", type="password", key="new_pass")
        if st.button("Create User"):
            if users_col.find_one({"username": new_user}):
                st.warning("⚠️ User already exists!")
            else:
                users_col.insert_one({"username": new_user, "password": hash_password(new_pass)})
                st.success("✅ User created successfully!")

    # Add Product
    with tab2:
        st.subheader("Add Product")
        prod_name = st.text_input("Product Name", key="prod_name")
        prod_price = st.number_input("Price (₹)", min_value=1, key="prod_price")
        if st.button("Add Product"):
            products_col.insert_one({"name": prod_name, "price": prod_price})
            st.success("✅ Product added successfully!")

    # View Data
    with tab3:
        st.subheader("Users")
        users = list(users_col.find({}, {"_id": 0, "password": 0}))
        st.table(users or [{"info": "No users"}])

        st.subheader("Products")
        products = list(products_col.find({}, {"_id": 0}))
        st.table(products or [{"info": "No products"}])

        st.subheader("Orders")
        orders = list(orders_col.find({}, {"_id": 0}))
        st.table(orders or [{"info": "No orders"}])

# ----------------------------
# User Dashboard
# ----------------------------
def user_dashboard(username):
    st.title(f"🛍️ Welcome, {username}")

    if "cart" not in st.session_state:
        st.session_state.cart = []

    tab1, tab2, tab3 = st.tabs(["🛒 Browse Products", "🧺 View Cart", "✅ Place Order"])

    # Browse Products
    with tab1:
        st.subheader("Available Products")
        products = list(products_col.find({}, {"_id": 0}))
        if not products:
            st.warning("No products available right now.")
        else:
            cols = st.columns(3)
            for i, product in enumerate(products):
                col = cols[i % 3]
                with col:
                    st.markdown(f"**{product['name']}**")
                    st.write(f"₹{product['price']}")
                    if st.button(f"Add to Cart - {product['name']}", key=f"add_{i}"):
                        st.session_state.cart.append(product)
                        st.success(f"Added {product['name']} to cart")

    # View Cart
    with tab2:
        st.subheader("🧺 Your Cart")
        if st.session_state.cart:
            total = sum(p["price"] for p in st.session_state.cart)
            for p in st.session_state.cart:
                st.write(f"- {p['name']} ₹{p['price']}")
            st.write(f"### 💰 Total: ₹{total}")
        else:
            st.info("Your cart is empty.")

    # Place Order
    with tab3:
        st.subheader("Place Your Order")
        if st.session_state.cart:
            total = sum(p["price"] for p in st.session_state.cart)
            if st.button("Confirm Order"):
                orders_col.insert_one({
                    "username": username,
                    "items": st.session_state.cart,
                    "total": total
                })
                st.session_state.cart = []
                st.success("🎉 Order placed successfully!")
        else:
            st.info("Add items to cart first!")

# ----------------------------
# Main App Logic
# ----------------------------
def main():
    st.set_page_config(page_title="Online Store", page_icon="🛍️", layout="centered")

    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "username" not in st.session_state:
        st.session_state.username = ""

    # Sidebar logout
    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            st.session_state.page = "home"
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            safe_rerun()

    # Home Page
    if st.session_state.page == "home":
        st.title("🏬 Online Store")
        st.write("Welcome! Please choose your role:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("👨‍💼 Login as Admin"):
                st.session_state.page = "admin_login"
                safe_rerun()
        with col2:
            if st.button("🧑‍💻 Login as User"):
                st.session_state.page = "user_login"
                safe_rerun()

    # Admin Login Page
    elif st.session_state.page == "admin_login":
        st.title("👨‍💼 Admin Login")
        username = st.text_input("Admin Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                safe_rerun()
            else:
                st.error("Invalid admin credentials!")

    # User Login Page
    elif st.session_state.page == "user_login":
        st.title("🧑‍💻 User Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = login_user(username, password)
            if role == "user":
                st.session_state.logged_in = True
                st.session_state.role = "user"
                st.session_state.username = username
                safe_rerun()
            else:
                st.error("Invalid user credentials!")

    # Dashboards
    elif st.session_state.logged_in:
        if st.session_state.role == "admin":
            admin_dashboard()
        elif st.session_state.role == "user":
            user_dashboard(st.session_state.username)

if __name__ == "__main__":
    main()
