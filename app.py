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

def login_user(username, password):
    """Check credentials for both admin and user."""
    admin_user = st.secrets["admin"]["username"]
    admin_pass = st.secrets["admin"]["password"]
    if username == admin_user and password == admin_pass:
        return "admin"
    user = users_col.find_one({"username": username, "password": hash_password(password)})
    if user:
        return "user"
    return None

def safe_rerun():
    try:
        st.rerun()
    except Exception:
        st.experimental_rerun()

# ----------------------------
# Admin Dashboard
# ----------------------------
def admin_page():
    st.title("🛒 Admin Dashboard")
    tab1, tab2, tab3 = st.tabs(["👤 Create User", "📦 Add Product", "📋 View Data"])

    # Create user tab
    with tab1:
        st.header("Create User")
        new_user = st.text_input("Username", key="new_user")
        new_pass = st.text_input("Password", type="password", key="new_pass")
        if st.button("Create User"):
            if users_col.find_one({"username": new_user}):
                st.warning("User already exists!")
            else:
                users_col.insert_one({"username": new_user, "password": hash_password(new_pass)})
                st.success("✅ User created successfully!")

    # Add product tab
    with tab2:
        st.header("Add Product")
        name = st.text_input("Product Name", key="prod_name")
        price = st.number_input("Price (₹)", min_value=1, key="prod_price")
        if st.button("Add Product"):
            products_col.insert_one({"name": name, "price": price})
            st.success("✅ Product added successfully!")

    # View data tab
    with tab3:
        st.header("All Users")
        users = list(users_col.find({}, {"_id": 0, "password": 0}))
        st.table(users or [{"info": "No users"}])

        st.header("All Products")
        prods = list(products_col.find({}, {"_id": 0}))
        st.table(prods or [{"info": "No products"}])

        st.header("All Orders")
        orders = list(orders_col.find({}, {"_id": 0}))
        st.table(orders or [{"info": "No orders"}])

# ----------------------------
# User Dashboard
# ----------------------------
def user_page(username):
    st.title(f"Welcome, {username} 🛍️")

    tab1, tab2, tab3 = st.tabs(["🛒 Shop", "🧺 My Cart", "✅ Checkout"])

    if "cart" not in st.session_state:
        st.session_state.cart = []

    # --- SHOP TAB ---
    with tab1:
        st.subheader("Available Products")
        products = list(products_col.find({}, {"_id": 0}))
        if not products:
            st.warning("No products available.")
        else:
            cols = st.columns(3)
            for i, p in enumerate(products):
                col = cols[i % 3]
                with col:
                    st.markdown(f"**{p['name']}**")
                    st.text(f"₹{p['price']}")
                    if st.button(f"Add {p['name']}", key=f"add_{p['name']}"):
                        st.session_state.cart.append(p)
                        st.success(f"Added {p['name']}")

    # --- CART TAB ---
    with tab2:
        st.subheader("🧺 Your Cart")
        if st.session_state.cart:
            total = sum(p["price"] for p in st.session_state.cart)
            for p in st.session_state.cart:
                st.write(f"- {p['name']} ₹{p['price']}")
            st.write(f"### 💰 Total: ₹{total}")
        else:
            st.info("Your cart is empty.")

    # --- CHECKOUT TAB ---
    with tab3:
        if st.session_state.cart:
            st.subheader("Order Summary")
            total = sum(p["price"] for p in st.session_state.cart)
            for p in st.session_state.cart:
                st.write(f"- {p['name']} ₹{p['price']}")
            st.write(f"### Total: ₹{total}")
            if st.button("Place Order"):
                orders_col.insert_one({
                    "username": username,
                    "items": st.session_state.cart,
                    "total": total
                })
                st.session_state.cart = []
                st.success("🎉 Order placed successfully!")
        else:
            st.info("Your cart is empty.")

# ----------------------------
# Main App
# ----------------------------
def main():
    st.set_page_config(page_title="Sales Management App", page_icon="🛒", layout="centered")

    # Session state initialization
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = ""

    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username =_
