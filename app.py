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

# Hash function for passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Admin credentials from secrets
ADMIN_USER = st.secrets["admin"]["username"]
ADMIN_PASS = st.secrets["admin"]["password"]

# --- Authentication ---
def login(username, password):
    if username == ADMIN_USER and password == ADMIN_PASS:
        return "admin"
    user = users_col.find_one({"username": username, "password": hash_password(password)})
    if user:
        return "user"
    return None

# --- Admin Page ---
def admin_page():
    st.title("🛒 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(["Create User", "Add Product", "View Data"])

    with tab1:
        st.header("Create User")
        new_user = st.text_input("Username", key="create_user_username")
        new_pass = st.text_input("Password", type="password", key="create_user_password")
        if st.button("Create User", key="create_user_button"):
            if users_col.find_one({"username": new_user}):
                st.warning("User already exists!")
            else:
                users_col.insert_one({"username": new_user, "password": hash_password(new_pass)})
                st.success("✅ User created successfully!")

    with tab2:
        st.header("Add Product")
        prod_name = st.text_input("Product Name", key="add_product_name")
        prod_price = st.number_input("Price (₹)", min_value=1, key="add_product_price")
        if st.button("Add Product", key="add_product_button"):
            products_col.insert_one({"name": prod_name, "price": prod_price})
            st.success("✅ Product added successfully!")

    with tab3:
        st.header("All Users")
        users = list(users_col.find({}, {"_id": 0, "password": 0}))
        if users:
            st.table(users)
        else:
            st.info("No users yet.")

        st.header("All Products")
        prods = list(products_col.find({}, {"_id": 0}))
        if prods:
            st.table(prods)
        else:
            st.info("No products yet.")

        st.header("All Orders")
        orders = list(orders_col.find({}, {"_id": 0}))
        if orders:
            st.table(orders)
        else:
            st.info("No orders yet.")

# --- User Page ---
def user_page(username):
    st.title(f"Welcome, {username} 🛍️")

    products = list(products_col.find({}, {"_id": 0}))
    if not products:
        st.warning("No products available.")
        return

    st.subheader("Available Products")
    cols = st.columns(3)
    cart = []

    for i, product in enumerate(products):
        col = cols[i % 3]
        with col:
            st.write(f"**{product['name']}** - ₹{product['price']}")
            if st.button(f"Add to Cart - {product['name']}", key=f"btn_add_{i}"):
                cart.append(product)

    if st.button("🛒 Buy Now", key="buy_now_button"):
        if cart:
            total = sum(p["price"] for p in cart)
            orders_col.insert_one({"username": username, "items": cart, "total": total})
            st.success(f"✅ Order placed successfully! Total ₹{total}")
        else:
            st.warning("Please add items to your cart first.")

# --- Main ---
def main():
    st.set_page_config(page_title="Online Store", page_icon="🛒", layout="centered")
    st.title("Online Store 🏬")

    menu = ["Login"]
    choice = st.sidebar.selectbox("Menu", menu, key="sidebar_menu")

    if choice == "Login":
        st.subheader("Login Page")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_button"):
            role = login(username, password)
            if role == "admin":
                admin_page()
            elif role == "user":
                user_page(username)
            else:
                st.error("Invalid credentials!")

if __name__ == "__main__":
    main()
