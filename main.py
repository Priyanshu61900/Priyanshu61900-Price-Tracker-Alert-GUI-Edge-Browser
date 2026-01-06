import os
import threading
import time
from datetime import datetime
import tkinter as tk
from tkinter import messagebox, scrolledtext
import requests

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ================= CONFIG =================
CHECK_INTERVAL = 300  # seconds (5 minutes)
EDGE_DRIVER_PATH = r"C:\Users\ASUS\Desktop\sel\msedgedriver.exe"  # Correct path

EMAILJS_SERVICE_ID = "your id(service)"
EMAILJS_TEMPLATE_ID = "your id(template)"
EMAILJS_PUBLIC_KEY = "your id(public emailjs key)"
# =========================================

tracking = False

# ================= LOGGING =================
def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    console.configure(state="normal")
    console.insert(tk.END, f"[{ts}] {msg}\n")
    console.configure(state="disabled")
    console.yview(tk.END)

# ================= EMAIL =================
def send_email(receiver_email, price):
    log("Sending email via EmailJS...")
    payload = {
        "service_id": EMAILJS_SERVICE_ID,
        "template_id": EMAILJS_TEMPLATE_ID,
        "user_id": EMAILJS_PUBLIC_KEY,
        "template_params": {
            "to_email": receiver_email,
            "message": f"🚨 Price dropped!\nCurrent price: {price}"
        }
    }
    try:
        r = requests.post("https://api.emailjs.com/api/v1.0/email/send", json=payload, timeout=10)
        if r.status_code == 200:
            log("Email sent successfully")
        else:
            log(f"EmailJS failed: {r.status_code} {r.text}")
    except Exception as e:
        log(f"EmailJS exception: {e}")

# ================= SELENIUM =================
def get_price(url):
    if not os.path.exists(EDGE_DRIVER_PATH):
        raise Exception(f"Edge driver not found at {EDGE_DRIVER_PATH}")

    log("Launching Edge browser...")
    options = Options()
    options.add_argument("--window-size=1920,1080")
    # options.add_argument("--headless=new")  # optional for headless
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )

    driver = webdriver.Edge(service=Service(EDGE_DRIVER_PATH), options=options)

    try:
        driver.get(url)
        wait = WebDriverWait(driver, 25)  # wait up to 25s
        price_text = ""

        if "amazon" in url.lower():
            selectors = [
                "span.a-price-whole",
                "span.a-price > span.a-offscreen",
                "span#priceblock_ourprice",
                "span#priceblock_dealprice"
            ]
        elif "ebay" in url.lower():
            selectors = [
                "#prcIsum",
                "[itemprop='price']",
                ".x-price-primary span"
            ]
        else:
            raise Exception("Unsupported website")

        for sel in selectors:
            try:
                el = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sel)))
                txt = el.text.strip()
                if txt:
                    price_text = txt
                    break
            except TimeoutException:
                continue

        if not price_text:
            raise Exception("Price not found or blocked")

        log(f"Raw price text: {price_text}")
        price_clean = price_text.replace("₹","").replace("$","").replace(",","").replace("INR","").strip()
        return float(price_clean)

    finally:
        driver.quit()
        log("Browser closed")

# ================= TRACKING =================
def track_price():
    global tracking
    url = url_entry.get().strip()
    email = email_entry.get().strip()

    # Sanitize target price
    target_text = target_entry.get().replace(",", "").strip()
    try:
        target = float(target_text)
    except:
        log(f"ERROR: Invalid target price '{target_entry.get()}'")
        tracking = False
        return

    log("Tracking started")

    while tracking:
        try:
            price = get_price(url)
            status_label.config(text=f"Current Price: {price}")
            log(f"Current price: {price}")

            if price <= target:
                log("Target price reached!")
                send_email(email, price)
                messagebox.showinfo("Alert", f"Price dropped to {price}! Email sent.")
                tracking = False
                log("Tracking stopped after alert")
                break

        except Exception as e:
            log(f"ERROR in tracking loop: {e}")

        time.sleep(CHECK_INTERVAL)

def start_tracking():
    global tracking
    if not url_entry.get() or not target_entry.get() or not email_entry.get():
        messagebox.showerror("Error", "URL, target price, and email are required")
        return
    if tracking:
        log("Tracker already running. Stop it first!")
        return
    tracking = True
    threading.Thread(target=track_price, daemon=True).start()
    status_label.config(text="Tracking...")
    log("Start button clicked")

def stop_tracking():
    global tracking
    tracking = False
    status_label.config(text="Stopped")
    log("Tracking manually stopped")

# ================= GUI =================
root = tk.Tk()
root.title("Price Tracker (Edge)")
root.geometry("720x560")

tk.Label(root, text="Product URL").pack()
url_entry = tk.Entry(root, width=95)
url_entry.pack(pady=2)

tk.Label(root, text="Target Price").pack()
target_entry = tk.Entry(root)
target_entry.pack(pady=2)

tk.Label(root, text="Receiver Email").pack()
email_entry = tk.Entry(root, width=50)
email_entry.pack(pady=2)

tk.Button(root, text="Start Tracking", bg="green", fg="white",
          command=start_tracking, width=25).pack(pady=6)

tk.Button(root, text="Stop Tracking", bg="red", fg="white",
          command=stop_tracking, width=25).pack(pady=4)

status_label = tk.Label(root, text="Idle", fg="blue")
status_label.pack(pady=5)

tk.Label(root, text="Console / Logs").pack()
console = scrolledtext.ScrolledText(root, height=15, state="disabled")
console.pack(fill="both", padx=10, pady=5)

root.mainloop()
