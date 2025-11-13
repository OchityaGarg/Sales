import streamlit as st
from pymongo import MongoClient
import hashlib

# ---------------------------------------------------------
# MongoDB CONNECTION
# ---------------------------------------------------------
client = MongoClient(st.secrets["mongodb"]["uri"])
db = client[st.secrets["mongodb"]["database"]]
users_col = db["users"]
products_col = db["products"]
orders_col = db["orders"]

# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def login_user(username, password):
    """Check if user exists or if admin credentials match."""
    if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
        return "admin"
    user = users_col.find_one({"username": username, "password": hash_password(password)})
    if user:
        return "user"
    return None

# ---------------------------------------------------------
# ADMIN DASHBOARD
# ---------------------------------------------------------
def admin_dashboard():
    st.title("🛒 Admin Dashboard")

    tab1, tab2, tab3 = st.tabs(["👤 Create User", "📦 Add Product", "📋 View Data"])

    # CREATE USER
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

    # ADD PRODUCT
    with tab2:
        st.subheader("Add Product")
        prod_name = st.text_input("Product Name", key="prod_name")
        prod_price = st.number_input("Price (₹)", min_value=1, key="prod_price")

        if st.button("Add Product"):
            products_col.insert_one({"name": prod_name, "price": prod_price})
            st.success("✅ Product added!")

    # VIEW ALL DATA
    with tab3:
        st.subheader("Users")
        users = list(users_col.find({}, {"_id": 0, "password": 0}))
        st.table(users or [{"info": "No users found"}])

        st.subheader("Products")
        prods = list(products_col.find({}, {"_id": 0}))
        st.table(prods or [{"info": "No products found"}])

        st.subheader("Orders")
        orders = list(orders_col.find({}, {"_id": 0}))
        st.table(orders or [{"info": "No orders found"}])


# ---------------------------------------------------------
# USER DASHBOARD
# ---------------------------------------------------------
def user_dashboard(username):
    st.title(f"🛍️ Welcome, {username}")

    # Initialize cart
    if "cart" not in st.session_state:
        st.session_state.cart = []

    tab1, tab2, tab3 = st.tabs(["🛒 Browse Products", "🧺 View Cart", "✅ Checkout"])

    # -------------------------------------------------
    # 1) BROWSE PRODUCTS
    # -------------------------------------------------
    with tab1:
        st.subheader("Available Products")
        products = list(products_col.find({}, {"_id": 0}))

        if not products:
            st.info("No products available.")
        else:
            cols = st.columns(3)
            for i, p in enumerate(products):
                col = cols[i % 3]
                with col:
                    st.markdown(f"**{p['name']}**")
                    st.write(f"₹{p['price']}")

                    if st.button(f"Add to Cart - {p['name']}", key=f"add_{i}"):
                        st.session_state.cart.append({"name": p["name"], "price": p["price"], "qty": 1})
                        st.success(f"Added {p['name']}!")

    # -------------------------------------------------
    # 2) EDITABLE CART
    # -------------------------------------------------
    with tab2:
        st.subheader("🧺 Your Cart (Editable)")

        if st.session_state.cart:

            updated_cart = []

            # Cart Table Header
            col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 3, 2])
            col1.write("**Product**")
            col2.write("**Price**")
            col3.write("**Qty**")
            col4.write("**Change Qty**")
            col5.write("**Remove**")

            for i, item in enumerate(st.session_state.cart):

                col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 3, 2])

                with col1:
                    st.write(f"**{item['name']}**")

                with col2:
                    st.write(f"₹{item['price']}")

                with col3:
                    st.write(item["qty"])

                with col4:
                    new_qty = st.selectbox(
                        "Qty",
                        list(range(1, 21)),
                        index=item["qty"] - 1,
                        key=f"qty_{i}"
                    )
                    item["qty"] = new_qty

                with col5:
                    if st.button("🗑️", key=f"del_{i}"):
                        item["qty"] = 0

                if item["qty"] > 0:
                    updated_cart.append(item)

            st.session_state.cart = updated_cart

            total = sum(p["price"] * p["qty"] for p in st.session_state.cart)
            st.markdown(f"### 💰 Total: ₹{total}")

            if st.button("🧹 Clear Cart"):
                st.session_state.cart = []
                st.success("Cart cleared!")
                st.rerun()
