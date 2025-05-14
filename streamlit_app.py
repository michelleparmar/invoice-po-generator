import streamlit as st
import pandas as pd
import zipfile
import os
import shutil
from io import BytesIO
from fpdf import FPDF
import random
from datetime import datetime, timedelta
from PIL import Image

st.set_page_config(page_title="Invoice & PO Generator", layout="centered")
st.title("📄 Generate Sample Invoices and Purchase Orders")

output_dir = "output_docs"
os.makedirs(output_dir, exist_ok=True)

def money(val):
    return f"${val:,.2f}"

def generate_number(prefix, idx):
    return f"{prefix}-{datetime.today().year}-{10000 + idx}"

def clean_logo_map(uploaded_files):
    logo_map = {}
    if uploaded_files:
        for file in uploaded_files:
            try:
                with Image.open(file) as img:
                    img.verify()
                logo_map[os.path.splitext(os.path.basename(file.name))[0].lower()] = file
            except:
                continue
    return logo_map

def create_document(index, supplier_name, supplier_address, customer_name, items, mode, invoice_logo_map, po_logo_map):
    po_number = generate_number("FER", index)
    invoice_number = generate_number("INV", index)
    invoice_date = datetime.today().strftime("%Y-%m-%d")
    po_date = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    shipping_type = random.choice(["FedEx Priority", "UPS Ground", "DHL Express"])
    payment_terms = random.choice(["2% net 10, net 30", "Net 30", "Net 45"])

    subtotal = sum(qty * price for _, _, qty, price in items)
    tax = round(subtotal * 0.065, 2)
    shipping = random.randint(100, 400)
    total = subtotal + tax + shipping

    def render_pdf(filename, is_invoice):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_margins(10, 10, 10)
        pdf.set_font("Arial", size=9)

        logo_map = invoice_logo_map if is_invoice else po_logo_map
        logo_key = supplier_name.lower()
        if logo_key in logo_map:
            try:
                pdf.image(logo_map[logo_key], 10, 8, 50)
            except:
                pass

        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "INVOICE" if is_invoice else "PURCHASE ORDER", ln=True, align="R")

        pdf.set_font("Arial", size=9)
        pdf.cell(0, 8, f"{'Invoice' if is_invoice else 'PO'} Number: {invoice_number if is_invoice else po_number}", ln=True, align="R")
        if is_invoice:
            pdf.cell(0, 8, f"PO Number: {po_number}", ln=True, align="R")
        pdf.cell(0, 8, f"Date: {invoice_date if is_invoice else po_date}", ln=True, align="R")

        pdf.ln(10)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 8, "Vendor:", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.multi_cell(0, 8, f"{supplier_name} Supply\n{supplier_address}")

        pdf.ln(4)
        pdf.set_font("Arial", "B", 9)
        pdf.cell(0, 8, "Bill To:", ln=True)
        pdf.set_font("Arial", size=9)
        pdf.multi_cell(0, 8, f"{customer_name}\nATTN: Accounts Payable")

        if not is_invoice:
            pdf.ln(4)
            pdf.set_font("Arial", "B", 9)
            pdf.cell(40, 8, "Shipping Method:")
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 8, shipping_type, ln=True)

        if is_invoice:
            pdf.set_font("Arial", "B", 9)
            pdf.cell(40, 8, "Terms:")
            pdf.set_font("Arial", size=9)
            pdf.cell(0, 8, payment_terms, ln=True)

        pdf.ln(4)
        headers = ["Product Name", "Code", "Qty", "Unit Price", "Line Total"]
        col_widths = [70, 35, 15, 25, 30]
        pdf.set_font("Arial", "B", 9)
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, 1)
        pdf.ln()

        pdf.set_font("Arial", size=9)
        for name, code, qty, price in items:
            line_total = qty * price
            pdf.cell(col_widths[0], 8, name[:40], 1)
            pdf.cell(col_widths[1], 8, code, 1)
            pdf.cell(col_widths[2], 8, str(qty), 1)
            pdf.cell(col_widths[3], 8, money(price), 1)
            pdf.cell(col_widths[4], 8, money(line_total), 1)
            pdf.ln()

        pdf.ln(4)
        pdf.cell(0, 8, f"Subtotal: {money(subtotal)}", ln=True, align="R")
        pdf.cell(0, 8, f"Tax: {money(tax)}", ln=True, align="R")
        if is_invoice:
            pdf.cell(0, 8, f"Shipping: {money(shipping)}", ln=True, align="R")
        pdf.cell(0, 8, f"Total: {money(total)}", ln=True, align="R")

        pdf.output(os.path.join(output_dir, filename))

    if mode in ("Both", "Invoice"):
        render_pdf(f"Invoice_{index:04d}.pdf", is_invoice=True)
    if mode in ("Both", "PO"):
        render_pdf(f"PO_{index:04d}.pdf", is_invoice=False)

# UI
st.subheader("1. Upload product CSV or use preset")
use_preset = st.checkbox("Use example product CSV")
product_file = None
if not use_preset:
    product_file = st.file_uploader("Upload product CSV", type="csv")

st.subheader("2. Upload logos (optional)")
invoice_logos = st.file_uploader("Supplier Logos for Invoices", type=["png", "jpg"], accept_multiple_files=True)
po_logos = st.file_uploader("Buyer Logos for POs", type=["png", "jpg"], accept_multiple_files=True)

st.subheader("3. Settings")
customer_name = st.text_input("Customer name for POs", value="Ferguson Enterprises, LLC")
mode = st.selectbox("Generate", ["Invoice", "PO", "Both"])
doc_count = st.slider("Number of documents (pairs if Both selected)", 1, 50, 5)

if st.button("Generate Documents"):
    try:
        if use_preset:
            df = pd.DataFrame({
                "supplier": ["Moen", "GE", "Kohler", "Copeland", "Hydromatic"] * 10,
                "product_name": ["Widget A", "Widget B", "Widget C", "Widget D", "Widget E"] * 10,
                "product_code": ["A1", "B2", "C3", "D4", "E5"] * 10,
                "unit_price": [99.99, 129.99, 149.99, 89.99, 109.99] * 10
            })
        else:
            df = pd.read_csv(product_file)

        invoice_logo_map = clean_logo_map(invoice_logos)
        po_logo_map = clean_logo_map(po_logos)

        shutil.rmtree(output_dir)
        os.makedirs(output_dir, exist_ok=True)

        used_suppliers = set()
        index = 1
        for _, row in df.iterrows():
            supplier = row["supplier"]
            if supplier in used_suppliers:
                continue
            supplier_products = df[df["supplier"] == supplier].sample(n=min(5, len(df[df["supplier"] == supplier])))
            items = [
                (r["product_name"], r["product_code"], random.randint(5, 25), r["unit_price"])
                for _, r in supplier_products.iterrows()
            ]
            create_document(index, supplier, f"{random.randint(100,999)} {supplier} Rd, City, ST", customer_name, items, mode, invoice_logo_map, po_logo_map)
            used_suppliers.add(supplier)
            index += 1
            if index > doc_count:
                break

        zip_buf = BytesIO()
        with zipfile.ZipFile(zip_buf, "w") as zipf:
            for filename in os.listdir(output_dir):
                zipf.write(os.path.join(output_dir, filename), filename)
        zip_buf.seek(0)

        st.success("✅ Documents generated successfully!")
        st.download_button("📥 Download ZIP", data=zip_buf, file_name="generated_docs.zip", mime="application/zip")

    except Exception as e:
        st.error(f"❌ Error: {e}")
# Full streamlit app code will be inserted here.
