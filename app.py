import json
import os
import secrets
from datetime import datetime
from pathlib import Path

from flask import Flask, abort, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = ROOT / "static" / "uploads"
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app = Flask(__name__)
app.secret_key = os.environ.get("GHAR_MITRA_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

SEED_DATA = {
    "workers.json": [
        {
            "id": "worker-rajesh-kumar",
            "name": "Rajesh Kumar",
            "mobile": "9876543210",
            "category": "Electrician",
            "experience": "8 years",
            "city": "Jaipur",
            "area": "Vaishali Nagar",
            "pincode": "302021",
            "address": "Vaishali Nagar, Jaipur, Rajasthan",
            "description": "Home wiring, fan and light installation, and electrical repairs.",
            "services": ["Home wiring", "Electrical repairs", "Fan installation"],
            "hours": "Mon–Sat, 9:00 AM–6:00 PM",
            "image": "",
            "status": "approved",
            "owner_id": None,
        },
        {
            "id": "worker-sunil-sharma",
            "name": "Sunil Sharma",
            "mobile": "9876543211",
            "category": "Plumber",
            "experience": "6 years",
            "city": "Jaipur",
            "area": "Mansarovar",
            "pincode": "302020",
            "address": "Mansarovar, Jaipur, Rajasthan",
            "description": "Tap, pipe, bathroom fitting, and water leakage repair.",
            "services": ["Pipe repair", "Bathroom fittings", "Leak detection"],
            "hours": "Mon–Sat, 8:00 AM–7:00 PM",
            "image": "",
            "status": "approved",
            "owner_id": None,
        },
        {
            "id": "worker-mohan-lal",
            "name": "Mohan Lal",
            "mobile": "9876543212",
            "category": "Mistri",
            "experience": "12 years",
            "city": "Jaipur",
            "area": "Malviya Nagar",
            "pincode": "302017",
            "address": "Malviya Nagar, Jaipur, Rajasthan",
            "description": "Masonry, plastering, tile work, and small construction projects.",
            "services": ["Masonry", "Plastering", "Tile work"],
            "hours": "Mon–Sat, 8:00 AM–5:00 PM",
            "image": "",
            "status": "approved",
            "owner_id": None,
        },
    ],
    "shops.json": [
        {
            "id": "shop-shree-cement",
            "name": "Shree Cement & Building Supplies",
            "owner_name": "Amit Jain",
            "mobile": "9876543220",
            "category": "Cement",
            "city": "Jaipur",
            "area": "Vaishali Nagar",
            "pincode": "302021",
            "address": "Main Market, Vaishali Nagar, Jaipur",
            "description": "Cement, putty, and everyday building supplies.",
            "services": ["Cement", "Wall putty", "Delivery enquiries"],
            "hours": "Mon–Sat, 9:00 AM–8:00 PM",
            "status": "approved",
            "owner_id": None,
        },
        {
            "id": "shop-jaipur-hardware",
            "name": "Jaipur Hardware House",
            "owner_name": "Neeraj Gupta",
            "mobile": "9876543221",
            "category": "Hardware",
            "city": "Jaipur",
            "area": "Mansarovar",
            "pincode": "302020",
            "address": "New Sanganer Road, Mansarovar, Jaipur",
            "description": "Tools, fasteners, plumbing fittings, and home hardware.",
            "services": ["Hardware", "Plumbing fittings", "Tools"],
            "hours": "Mon–Sat, 10:00 AM–8:00 PM",
            "status": "approved",
            "owner_id": None,
        },
    ],
    "users.json": [],
    "requests.json": [],
    "messages.json": [],
}


def read_data(filename):
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    if not path.exists():
        write_data(filename, SEED_DATA.get(filename, []))
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as error:
        app.logger.exception("Could not read %s", path)
        raise RuntimeError(f"Unable to read application data file: {filename}") from error
    if not isinstance(data, list):
        raise RuntimeError(f"Application data file must contain a JSON list: {filename}")
    return data


def write_data(filename, data):
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temporary_path, path)
    except OSError:
        app.logger.exception("Could not save %s", path)
        raise


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return next((user for user in read_data("users.json") if user["id"] == user_id), None)


def require_login():
    if current_user() is None:
        flash("Please log in to continue.", "error")
        return redirect(url_for("login", next=request.path))
    return None


def find_record(filename, record_id):
    return next((record for record in read_data(filename) if record["id"] == record_id), None)


def filtered_records(records):
    area = request.args.get("area", "").strip().casefold()
    pincode = request.args.get("pincode", "").strip()
    location = request.args.get("location", "").strip()
    city = request.args.get("city", "").strip().casefold()
    category = request.args.get("category", "").strip().casefold()
    if location:
        if location.isdigit() and len(location) == 6:
            pincode = location
        else:
            area = location.casefold()
    results = []
    for record in records:
        if record.get("status") != "approved":
            continue
        if pincode and record.get("pincode") != pincode:
            continue
        if area and area not in record.get("area", "").casefold():
            continue
        if city and city not in record.get("city", "").casefold():
            continue
        if category and record.get("category", "").casefold() != category:
            continue
        results.append(record)
    return results


def save_profile_image(field_name):
    image = request.files.get(field_name)
    if image is None or not image.filename:
        return ""
    filename = secure_filename(image.filename)
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("Choose a JPG, PNG, or WEBP profile image.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{secrets.token_hex(12)}.{extension}"
    image.save(UPLOAD_DIR / stored_name)
    return f"uploads/{stored_name}"


def account_by_mobile(mobile):
    return next((user for user in read_data("users.json") if user["mobile"] == mobile), None)


def require_admin():
    user = current_user()
    if user is None:
        flash("Please log in as an administrator.", "error")
        return redirect(url_for("admin_login"))
    if user.get("role") != "admin":
        abort(403)
    return None


def validate_common_form(mobile, pincode):
    if not mobile.isdigit() or len(mobile) != 10:
        return "Enter a valid 10-digit Indian mobile number."
    if not pincode.isdigit() or len(pincode) != 6:
        return "Enter a valid 6-digit PIN code."
    return None


@app.context_processor
def inject_user():
    return {"logged_in_user": current_user()}


@app.route("/")
def home():
    return render_template(
        "home.html",
        workers=read_data("workers.json"),
        shops=read_data("shops.json"),
    )


@app.route("/about")
def about():
    return render_template(
        "static_page.html",
        title="About GharMitra",
        eyebrow="A better way to find local help",
        paragraphs=[
            "GharMitra helps households discover nearby home-service professionals and construction material shops.",
            "We want finding reliable local help to feel simpler, clearer, and more convenient. Provider listings are reviewed before they appear in search.",
            "Search results use the area, city, and PIN code supplied by providers. A PIN-code match is not an exact distance or a real-time GPS result.",
        ],
    )


@app.route("/workers")
def workers():
    all_workers = [record for record in read_data("workers.json") if record.get("status") == "approved"]
    return render_template(
        "listing.html",
        title="Find trusted workers",
        subtitle="Explore local professionals for repairs, maintenance, and construction.",
        records=filtered_records(all_workers),
        kind="worker",
        categories=sorted({item["category"] for item in all_workers}),
    )


@app.route("/shops")
def shops():
    all_shops = [record for record in read_data("shops.json") if record.get("status") == "approved"]
    return render_template(
        "listing.html",
        title="Find material shops",
        subtitle="Discover nearby suppliers for your home project.",
        records=filtered_records(all_shops),
        kind="shop",
        categories=sorted({item["category"] for item in all_shops}),
    )


@app.route("/categories")
def categories():
    worker_categories = sorted({item["category"] for item in read_data("workers.json") if item.get("status") == "approved"})
    shop_categories = sorted({item["category"] for item in read_data("shops.json") if item.get("status") == "approved"})
    return render_template("categories.html", worker_categories=worker_categories, shop_categories=shop_categories)


@app.route("/workers/<record_id>")
def worker_detail(record_id):
    record = find_record("workers.json", record_id)
    if record is None or record.get("status") != "approved":
        abort(404)
    saved = current_user() and record_id in current_user().get("saved_workers", [])
    return render_template("detail.html", record=record, kind="worker", saved=saved)


@app.route("/shops/<record_id>")
def shop_detail(record_id):
    record = find_record("shops.json", record_id)
    if record is None or record.get("status") != "approved":
        abort(404)
    return render_template("detail.html", record=record, kind="shop", saved=False)


@app.route("/register", methods=["GET", "POST"])
def register():
    return render_template("register.html")


@app.route("/register/customer", methods=["GET", "POST"])
def register_customer():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        error = None
        if not mobile.isdigit() or len(mobile) != 10:
            error = "Enter a valid 10-digit Indian mobile number."
        if error is None and (not name or len(password) < 8):
            error = "Enter your name and a password with at least 8 characters."
        if error is None and account_by_mobile(mobile):
            error = "An account with this mobile number already exists."
        if error:
            flash(error, "error")
            return render_template("register.html", form_type="customer", form=request.form)
        user_id = f"user-{secrets.token_hex(8)}"
        users = read_data("users.json")
        users.append({
            "id": user_id,
            "name": name,
            "mobile": mobile,
            "password_hash": generate_password_hash(password),
            "role": "customer",
            "saved_workers": [],
        })
        write_data("users.json", users)
        session["user_id"] = user_id
        flash("Your customer account is ready.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form_type="customer")


@app.route("/register/worker", methods=["GET", "POST"])
def register_worker():
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip() for key in (
            "name", "mobile", "category", "experience", "city", "area",
            "pincode", "address", "description", "hours", "password",
        )}
        error = validate_common_form(fields["mobile"], fields["pincode"])
        if error is None and not all(fields[key] for key in ("name", "category", "experience", "city", "area", "address", "description", "hours", "password")):
            error = "Please complete all required fields."
        if error is None and len(fields["password"]) < 8:
            error = "Use a password with at least 8 characters."
        if error is None and account_by_mobile(fields["mobile"]):
            error = "An account with this mobile number already exists."
        if error:
            flash(error, "error")
            return render_template("register.html", form_type="worker", form=request.form)
        try:
            image = save_profile_image("image")
            users = read_data("users.json")
            user_id = f"user-{secrets.token_hex(8)}"
            users.append({
                "id": user_id,
                "mobile": fields["mobile"],
                "password_hash": generate_password_hash(fields["password"]),
                "role": "worker",
                "saved_workers": [],
            })
            write_data("users.json", users)
            provider = {key: fields[key] for key in (
                "name", "mobile", "category", "experience", "city", "area",
                "pincode", "address", "description", "hours",
            )}
            provider.update({
                "id": f"worker-{secrets.token_hex(8)}",
                "services": [item.strip() for item in request.form.get("services", "").split(",") if item.strip()],
                "image": image,
                "status": "pending",
                "owner_id": user_id,
            })
            providers = read_data("workers.json")
            providers.append(provider)
            write_data("workers.json", providers)
        except (OSError, ValueError) as error:
            flash(str(error) or "The registration could not be saved.", "error")
            return render_template("register.html", form_type="worker", form=request.form)
        session["user_id"] = user_id
        flash("Your worker profile is submitted and is pending admin approval.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form_type="worker")


@app.route("/register/shop", methods=["GET", "POST"])
def register_shop():
    if request.method == "POST":
        fields = {key: request.form.get(key, "").strip() for key in (
            "name", "owner_name", "mobile", "category", "city", "area",
            "pincode", "address", "description", "hours", "password",
        )}
        error = validate_common_form(fields["mobile"], fields["pincode"])
        if error is None and not all(fields[key] for key in (
            "name", "owner_name", "category", "city", "area", "address",
            "description", "hours", "password",
        )):
            error = "Please complete all required fields."
        if error is None and len(fields["password"]) < 8:
            error = "Use a password with at least 8 characters."
        if error is None and account_by_mobile(fields["mobile"]):
            error = "An account with this mobile number already exists."
        if error:
            flash(error, "error")
            return render_template("register.html", form_type="shop", form=request.form)
        users = read_data("users.json")
        user_id = f"user-{secrets.token_hex(8)}"
        users.append({
            "id": user_id,
            "mobile": fields["mobile"],
            "password_hash": generate_password_hash(fields["password"]),
            "role": "shop",
            "saved_workers": [],
        })
        shops_data = read_data("shops.json")
        shop = {key: fields[key] for key in (
            "name", "owner_name", "mobile", "category", "city", "area",
            "pincode", "address", "description", "hours",
        )}
        shop.update({
            "id": f"shop-{secrets.token_hex(8)}",
            "services": [item.strip() for item in request.form.get("services", "").split(",") if item.strip()],
            "status": "pending",
            "owner_id": user_id,
        })
        try:
            write_data("users.json", users)
            shops_data.append(shop)
            write_data("shops.json", shops_data)
        except OSError:
            flash("The registration could not be saved. Please try again.", "error")
            return render_template("register.html", form_type="shop", form=request.form)
        session["user_id"] = user_id
        flash("Your shop profile is submitted and is pending admin approval.", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html", form_type="shop")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        user = account_by_mobile(mobile)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Mobile number or password is incorrect.", "error")
            return render_template("login.html")
        session.clear()
        session["user_id"] = user["id"]
        destination = request.args.get("next", "")
        if not destination.startswith("/") or destination.startswith("//"):
            destination = url_for("dashboard")
        return redirect(destination)
    return render_template("login.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        admin_mobile = os.environ.get("GHAR_MITRA_ADMIN_MOBILE", "9999999999")
        admin_password = os.environ.get("GHAR_MITRA_ADMIN_PASSWORD", "admin123")
        if mobile != admin_mobile or password != admin_password:
            flash("Administrator mobile number or password is incorrect.", "error")
            return render_template("admin_login.html")

        users = read_data("users.json")
        admin = next((user for user in users if user.get("role") == "admin"), None)
        if admin is None:
            admin = {
                "id": "user-admin",
                "name": "GharMitra Administrator",
                "mobile": admin_mobile,
                "password_hash": generate_password_hash(admin_password),
                "role": "admin",
                "saved_workers": [],
            }
            users.append(admin)
            write_data("users.json", users)
        elif admin["mobile"] != admin_mobile:
            admin["mobile"] = admin_mobile
            admin["password_hash"] = generate_password_hash(admin_password)
            write_data("users.json", users)

        session.clear()
        session["user_id"] = admin["id"]
        return redirect(url_for("admin_dashboard"))
    return render_template("admin_login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You are now logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    user = current_user()
    listing = None
    if user["role"] == "worker":
        listing = next((item for item in read_data("workers.json") if item.get("owner_id") == user["id"]), None)
    elif user["role"] == "shop":
        listing = next((item for item in read_data("shops.json") if item.get("owner_id") == user["id"]), None)
    incoming = [item for item in read_data("requests.json") if listing and item.get("worker_id") == listing["id"]]
    return render_template("dashboard.html", user=user, listing=listing, incoming=incoming)


@app.route("/admin")
def admin_dashboard():
    access_response = require_admin()
    if access_response:
        return access_response
    workers = read_data("workers.json")
    shops = read_data("shops.json")
    users = read_data("users.json")
    requests_data = read_data("requests.json")
    messages = read_data("messages.json")
    return render_template(
        "admin_dashboard.html",
        workers=workers,
        shops=shops,
        users=users,
        requests=requests_data,
        messages=messages,
    )


@app.route("/admin/moderate", methods=["POST"])
def admin_moderate():
    access_response = require_admin()
    if access_response:
        return access_response
    kind = request.form.get("kind")
    record_id = request.form.get("record_id")
    status = request.form.get("status")
    if kind not in ("worker", "shop") or status not in ("approved", "rejected", "pending"):
        flash("Invalid moderation request.", "error")
        return redirect(url_for("admin_dashboard"))
    filename = "workers.json" if kind == "worker" else "shops.json"
    records = read_data(filename)
    record = next((item for item in records if item["id"] == record_id), None)
    if record is None:
        flash("The listing could not be found.", "error")
    else:
        record["status"] = status
        write_data(filename, records)
        flash(f"{record['name']} is now {status}.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/profile", methods=["GET", "POST"])
def edit_profile():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    user = current_user()
    if user["role"] not in ("worker", "shop"):
        return redirect(url_for("dashboard"))
    filename = "workers.json" if user["role"] == "worker" else "shops.json"
    records = read_data(filename)
    listing = next((item for item in records if item.get("owner_id") == user["id"]), None)
    if listing is None:
        flash("No provider profile is linked to this account.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        keys = (
            ("name", "category", "experience", "city", "area", "pincode", "address", "description", "hours")
            if user["role"] == "worker"
            else ("name", "owner_name", "category", "city", "area", "pincode", "address", "description", "hours")
        )
        updated = {key: request.form.get(key, "").strip() for key in keys}
        mobile = request.form.get("mobile", "").strip()
        error = validate_common_form(mobile, updated["pincode"])
        if error is None and (not all(updated.values()) or not request.form.get("services", "").strip()):
            error = "Please complete all required fields."
        duplicate = account_by_mobile(mobile)
        if error is None and duplicate and duplicate["id"] != user["id"]:
            error = "An account with this mobile number already exists."
        if error:
            flash(error, "error")
            return render_template("profile.html", listing={**listing, **updated, "mobile": mobile}, role=user["role"])
        listing.update(updated)
        listing["mobile"] = mobile
        listing["services"] = [part.strip() for part in request.form["services"].split(",") if part.strip()]
        listing["status"] = "pending"
        if user["role"] == "worker":
            try:
                image = save_profile_image("image")
            except ValueError as image_error:
                flash(str(image_error), "error")
                return render_template("profile.html", listing={**listing, **updated, "mobile": mobile}, role=user["role"])
            if image:
                listing["image"] = image
        users = read_data("users.json")
        account = next(item for item in users if item["id"] == user["id"])
        account["mobile"] = mobile
        write_data(filename, records)
        write_data("users.json", users)
        flash("Profile updated and returned to pending approval.", "success")
        return redirect(url_for("dashboard"))
    return render_template("profile.html", listing=listing, role=user["role"])


@app.route("/requests", methods=["GET", "POST"])
def my_requests():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    user = current_user()
    requests_data = read_data("requests.json")
    if request.method == "POST":
        request_id = request.form.get("request_id", "")
        action = request.form.get("action", "")
        item = next((record for record in requests_data if record["id"] == request_id), None)
        providers = read_data("workers.json")
        owned_worker_ids = {provider["id"] for provider in providers if provider.get("owner_id") == user["id"]}
        if item and item.get("worker_id") in owned_worker_ids and action in ("accepted", "rejected"):
            item["status"] = action
            write_data("requests.json", requests_data)
            flash(f"Request {action}.", "success")
        else:
            flash("That request could not be updated.", "error")
        return redirect(url_for("my_requests"))
    if user["role"] == "worker":
        owned = {item["id"] for item in read_data("workers.json") if item.get("owner_id") == user["id"]}
        records = [item for item in requests_data if item.get("worker_id") in owned]
    else:
        records = [item for item in requests_data if item.get("customer_id") == user["id"]]
    return render_template("requests.html", records=records, role=user["role"])


@app.route("/saved", methods=["GET", "POST"])
def saved_workers():
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    user = current_user()
    if user["role"] != "customer":
        flash("Only customer accounts can save workers.", "error")
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        worker_id = request.form.get("worker_id", "")
        users = read_data("users.json")
        selected = next((item for item in users if item["id"] == user["id"]), None)
        provider = find_record("workers.json", worker_id)
        if selected and provider and provider.get("status") == "approved":
            saved = selected.setdefault("saved_workers", [])
            if worker_id in saved:
                saved.remove(worker_id)
            else:
                saved.append(worker_id)
            write_data("users.json", users)
        return redirect(request.referrer or url_for("saved_workers"))
    saved_ids = user.get("saved_workers", [])
    records = [item for item in read_data("workers.json") if item["id"] in saved_ids and item.get("status") == "approved"]
    return render_template("listing.html", title="Saved workers", subtitle="Your bookmarked local professionals.", records=records, kind="worker", categories=[])


@app.route("/request-service/<worker_id>", methods=["POST"])
def request_service(worker_id):
    redirect_response = require_login()
    if redirect_response:
        return redirect_response
    user = current_user()
    worker = find_record("workers.json", worker_id)
    if worker is None or worker.get("status") != "approved":
        abort(404)
    if user["role"] != "customer":
        flash("Only customer accounts can send work requests.", "error")
        return redirect(url_for("worker_detail", record_id=worker_id))
    description = request.form.get("description", "").strip()
    if not description:
        flash("Please describe the work you need.", "error")
        return redirect(url_for("worker_detail", record_id=worker_id))
    records = read_data("requests.json")
    records.append({
        "id": f"request-{secrets.token_hex(8)}",
        "worker_id": worker_id,
        "worker_name": worker["name"],
        "customer_id": user["id"],
        "customer_mobile": user["mobile"],
        "description": description,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "status": "pending",
    })
    write_data("requests.json", records)
    flash("Your demo work request has been sent.", "success")
    return redirect(url_for("my_requests"))


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        message = request.form.get("message", "").strip()
        if not all((name, mobile, message)):
            flash("Please complete each field.", "error")
        else:
            if not mobile.isdigit() or len(mobile) != 10:
                flash("Enter a valid 10-digit mobile number.", "error")
                return redirect(url_for("contact"))
            messages = read_data("messages.json")
            messages.append({
                "id": f"message-{secrets.token_hex(8)}",
                "name": name,
                "mobile": mobile,
                "message": message,
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            write_data("messages.json", messages)
            flash("Thanks for reaching out. We will be in touch.", "success")
        return redirect(url_for("contact"))
    return render_template("contact.html")


@app.route("/privacy")
def privacy():
    return render_template(
        "static_page.html",
        title="Privacy Policy",
        eyebrow="Your information matters",
        paragraphs=[
            "This starter site stores account, provider, and demo request data in local JSON files. Passwords are stored as one-way hashes.",
            "Contact details are shown only as part of approved public provider listings. Do not enter sensitive personal or financial information.",
            "This is an early demo. Before a public launch, add a complete privacy review, retention controls, secure deployment configuration, and a process for data access or deletion requests.",
        ],
    )


@app.route("/terms")
def terms():
    return render_template(
        "static_page.html",
        title="Terms and Conditions",
        eyebrow="Using GharMitra",
        paragraphs=[
            "GharMitra is a discovery platform. Users should independently confirm provider identity, availability, pricing, and work scope before making an agreement.",
            "Listings in this demo may be illustrative. A profile marked pending is not publicly searchable until approved.",
            "Search uses provider-entered locality and PIN code and does not guarantee distance, service availability, quality, or a particular outcome.",
        ],
    )


@app.errorhandler(404)
def not_found(_error):
    return render_template("static_page.html", title="Page not found", eyebrow="404", paragraphs=["We could not find that page."]), 404


@app.errorhandler(413)
def upload_too_large(_error):
    flash("That file is too large. The maximum upload size is 5 MB.", "error")
    return redirect(request.referrer or url_for("register_worker"))


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
