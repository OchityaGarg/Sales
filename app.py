import streamlit as st
from pymongo import MongoClient
import hashlib
from datetime import datetime
import uuid
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

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
    """Authenticate user or admin."""
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

    tab1, tab2, tab3 = st.tabs(["👤 Create User", "📦 Add Product", "📋 View Orders"])

    # CREATE USER TAB
    with tab1:
        st.subheader("Create New User")
        new_user = st.text_input("Username", key="new_user")
        new_pass = st.text_input("Password", type="password", key="new_pass")

        if st.button("Create User"):
            if users_col.find_one({"username": new_user}):
                st.warning("⚠ User already exists!")
            else:
                users_col.insert_one({"username": new_user, "password": hash_password(new_pass)})
                st.success("✅ User created successfully!")

    # ADD PRODUCT TAB
    with tab2:
        st.subheader("Add Product")
        prod_name = st.text_input("Product Name", key="prod_name")
        prod_price = st.number_input("Price (₹)", min_value=1, key="prod_price")

        if st.button("Add Product"):
            products_col.insert_one({"name": prod_name, "price": prod_price})
            st.success("✅ Product added!")

    # VIEW ORDERS TAB
    with tab3:
        st.subheader("All Orders")

        orders = list(orders_col.find({}, {"_id": 0}))

        if not orders:
            st.info("No orders found.")
        else:
            for order in orders:

                with st.expander(
                    f"📦 Order ID: {order['order_id']} | User: {order['username']} | Total: ₹{order['total']}"
                ):
                    st.markdown("### 🧾 Order Details")
                    st.write(f"**Order ID:** {order['order_id']}")
                    st.write(f"**Username:** {order['username']}")
                    st.write(f"**Date & Time:** {order['timestamp']}")
                    st.write(f"**Total Amount:** ₹{order['total']}")

                    st.write("---")
                    st.markdown("### 📦 Items Purchased")

                    # Table Header
                    col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
                    col1.write("**Product**")
                    col2.write("**Price**")
                    col3.write("**Qty**")
                    col4.write("**Subtotal**")

                    # Line Items
                    for item in order["items"]:
                        col1, col2, col3, col4 = st.columns([4, 2, 2, 2])
                        col1.write(item["name"])
                        col2.write(f"₹{item['price']}")
                        col3.write(item["qty"])
                        col4.write(f"₹{item['price'] * item['qty']}")

                    st.write("---")
                    st.markdown(f"### 🧮 Grand Total: **₹{order['total']}**")

                    st.write("---")

                    # INVOICE PDF BUTTON
                    if st.button(f"Download Invoice PDF for {order['order_id']}", key=f"pdf_{order['order_id']}"):
                        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                        c = canvas.Canvas(temp_file.name, pagesize=letter)

                        # Title
                        c.setFont("Helvetica-Bold", 20)
                        c.drawString(50, 750, "Invoice")

                        c.setFont("Helvetica", 12)
                        c.drawString(50, 720, f"Order ID: {order['order_id']}")
                        c.drawString(50, 700, f"Username: {order['username']}")
                        c.drawString(50, 680, f"Date: {order['timestamp']}")

                        c.drawString(50, 650, "Items:")

                        y = 630
                        for item in order["items"]:
                            c.drawString(60, y, f"{item['name']} (x{item['qty']}) — ₹{item['price'] * item['qty']}")
                            y -= 20

                        c.drawString(50, y - 20, f"Total: ₹{order['total']}")
                        c.save()

                        with open(temp_file.name, "rb") as f:
                            st.download_button(
                                label="📄 Download Invoice",
                                data=f,
                                file_name=f"Invoice_{order['order_id']}.pdf",
                                mime="application/pdf"
                            )


# ---------------------------------------------------------
# USER DASHBOARD
# ---------------------------------------------------------
def user_dashboard(username):
    st.title(f"🛍️ Welcome, {username}")

    if "cart" not in st.session_state:
        st.session_state.cart = []

    tab1, tab2, tab3 = st.tabs(["🛒 Browse Products", "🧺 View Cart", "✅ Checkout"])

    # -----------------------------------------------------
    # SHOP TAB
    # -----------------------------------------------------
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

    # -----------------------------------------------------
    # CART TAB (FULLY EDITABLE)
    # -----------------------------------------------------
    with tab2:
        st.subheader("🧺 Your Cart")

        if st.session_state.cart:

            updated_cart = []

            col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 3, 2])
            col1.write("**Product**")
            col2.write("**Price**")
            col3.write("**Qty**")
            col4.write("**Change Qty**")
            col5.write("**Remove**")

            for i, item in enumerate(st.session_state.cart):

                col1, col2, col3, col4, col5 = st.columns([4, 2, 2, 3, 2])

                with col1:
                    st.write(f"{item['name']}")

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
                    if st.button("🗑️", key=f"delete_{i}"):
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

        else:
            st.info("Your cart is empty.")

    # -----------------------------------------------------
    # CHECKOUT TAB
    # -----------------------------------------------------
    with tab3:
        st.subheader("Checkout")

        if st.session_state.cart:

            total = sum(p["price"] * p["qty"] for p in st.session_state.cart)

            st.markdown("### 🧾 Order Summary")
            for p in st.session_state.cart:
                st.write(f"- {p['name']} × {p['qty']} — ₹{p['price'] * p['qty']}")

            st.markdown(f"### 💵 Total: ₹{total}")

            if st.button("Place Order"):

                orders_col.insert_one({
                    "order_id": str(uuid.uuid4())[:8],
                    "username": username,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "items": st.session_state.cart,
                    "total": total
                })

                st.session_state.cart = []
                st.success("🎉 Order placed successfully!")

        else:
            st.info("Your cart is empty.")


# ---------------------------------------------------------
# MAIN APP LOGIC
# ---------------------------------------------------------
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

    # LOGOUT BUTTON
    if st.session_state.logged_in:
        if st.sidebar.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.page = "home"
            st.session_state.username = ""
            st.rerun()

    # -------------------------------
    # HOME PAGE
    # -------------------------------
    if st.session_state.page == "home":
        st.title("🏬 Online Store")
        col1, col2 = st.columns(2)

        with col1:
            if st.button("👨‍💼 Login as Admin"):
                st.session_state.page = "admin_login"
                st.rerun()

        with col2:
            if st.button("🧑‍💻 Login as User"):
                st.session_state.page = "user_login"
                st.rerun()

    # -------------------------------
    # ADMIN LOGIN
    # -------------------------------
    elif st.session_state.page == "admin_login":
        st.title("👨‍💼 Admin Login")

        username = st.text_input("Admin Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if username == st.secrets["admin"]["username"] and password == st.secrets["admin"]["password"]:
                st.session_state.logged_in = True
                st.session_state.role = "admin"
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid admin credentials!")

    # -------------------------------
    # USER LOGIN
    # -------------------------------
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
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid user credentials!")

    # -------------------------------
    # DASHBOARD ROUTER
    # -------------------------------
    elif st.session_state.logged_in and st.session_state.page == "dashboard":
        if st.session_state.role == "admin":
            admin_dashboard()
        else:
            user_dashboard(st.session_state.username)


if __name__ == "__main__":
    main()
