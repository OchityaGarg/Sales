import streamlit as st
from pymongo import MongoClient
import hashlib

# Connect to MongoDB using Streamlit secrets
client = MongoClient(st.secrets["mongodb"]["uri"])
db = client[st.secrets["mongodb"]["database"]]

# Collections
users_col = db["users"]
products_col = db["products"]
orders_col = db["orders"]

# --- Helper Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def safe_rerun():
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# --- Authentication ---
ADMIN_USER = st.secrets["admin"]["username"]
ADMIN_PASS = st.secrets["admin"]["password"]

def login(username, password):
    if username == ADMIN_USER and password == ADMIN_PASS:
        return "admin"
    user = users_col.find_one({"username": username, "password": hash_password(password)})
    if user:
        return "user"
    return None

# --- Admin Dashboard ---
def admin_page():
    st.title("🛒 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(["👤 Create User", "📦 Add Product", "📋 View Data"])

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

    with tab2:
        st.header("Add Product")
        name = st.text_input("Product Name", key="prod_name")
        price = st.number_input("Price (₹)", min_value=1, key="prod_price")
        if st.button("Add Product"):
            products_col.insert_one({"name": name, "price": price})
            st.success("✅ Product added successfully!")

    with tab3:
        st.header("All Users")
        users = list(users_col.find({}, {"_id": 0, "password": 0}))
        st.table(users if users else [{"info": "No users"}])

        st.header("All Products")
        prods = list(products_col.find({}, {"_id": 0}))
        st.table(prods if prods else [{"info": "No products"}])

        st.header("All Orders")
        orders = list(orders_col.find({}, {"_id": 0}))
        st.table(orders if orders else [{"info": "No orders"}])

# --- User Dashboard ---
def user_page(username):
    st.title(f"Welcome, {username} 🛍️")

    # Tabs for user flow
    tab1, tab2, tab3 = st.tabs(["🛒 Shop", "🧺 My Cart", "✅ Checkout"])

    # Ensure cart exists
    if "cart" not in st.session_state:
        st.session_state.cart = []

    # ---- SHOP TAB ----
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
                    st.text(f"₹{product['price']}")
                    if st.button(f"Add to Cart - {product['name']}", key=f"add_{i}"):
                        st.session_state.cart.append(product)
                        st.success(f"Added {product['name']}")

    # ---- CART TAB ----
    with tab2:
        st.subheader("🧺 Your Cart")
        if st.session_state.cart:
            cart_items = [f"{p['name']} - ₹{p['price']}" for p in st.session_state.cart]
            for item in cart_items:
                st.write(item)
            total = sum(p["price"] for p in st.session_state.cart)
            st.write(f"### 💰 Total: ₹{total}")
            if st.button("Proceed to Checkout"):
                st.session_state.checkout_ready = True
                st.success("Proceeding to checkout → Go to 'Checkout' tab")
        else:
            st.info("Your cart is empty.")

    # ---- CHECKOUT TAB ----
    with tab3:
        st.subheader("✅ Checkout")
        if st.session_state.cart:
            total = sum(p["price"] for p in st.session_state.cart)
            st.write("### Order Summary")
            for p in st.session_state.cart:
                st.write(f"- {p['name']} ₹{p['price']}")
            st.write(f"### 💵 Total: ₹{total}")
            if st.button("Place Order"):
                orders_col.insert_one({
                    "username": username,
                    "items": st.session_state.cart,
                    "total": total
                })
                st.session_state.cart = []
                st.success("🎉 Order placed successfully!")
        else:
            st.info("Your cart is empty. Please add items first.")

# --- Main Function ---
def main():
    st.set_page_config(page_title="Online Store", page_icon="🛒", layout="centered")
    st.title("Online Store 🏬")

    # Initialize session
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = ""

    # Sidebar logout
    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = ""
            st.success("Logged out successfully!")
            safe_rerun()

    # Login Page
    if not st.session_state.logged_in:
        st.subheader("🔐 Login Page")
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", key="login_btn"):
            role = login(username, password)
            if role:
                st.session_state.logged_in = True
                st.session_state.role = role
                st.session_state.username = username
                safe_rerun()
            else:
                st.error("Invalid credentials!")
    else:
        # Dashboard based on role
        if st.session_state.role == "admin":
            admin_page()
        else:
            user_page(st.session_state.username)

if __name__ == "__main__":
    main()
