from flask import Blueprint, flash, g, redirect, render_template, request, url_for, make_response, send_file
from werkzeug.exceptions import abort

from naturelifecert.auth import login_required
from naturelifecert.db import get_db

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import pathlib
import io

bp = Blueprint("pdf", __name__)


@bp.route("/")
def index():
    db = get_db()
    # Don't expose email address to the wild :)
    posts = db.execute(
        "SELECT p.id, first_name, last_name, country, donation, currency, created"
        " FROM post p JOIN user u ON p.author_id = u.id"
        " ORDER BY created DESC"
    ).fetchall()
    return render_template("pdf/index.html", posts=posts)


# TODO: Create and update could be bundled together
@bp.route("/create", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        first_name = request.form["first_name"]
        last_name = request.form["last_name"]
        country = request.form["country"]
        donation = request.form["donation"]
        currency = request.form["currency"]
        email = request.form["email"]
        error = None

        for key in ["first_name", "last_name", "country", "donation", "currency", "email"]:
            if not locals()[key]:
                # TODO: Check for real currency values
                # TODO: Check if real email
                error = f"{key} is required"

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO post (first_name, last_name, country, donation, currency, author_id, created)"
                " VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)",
                (first_name, last_name, country, donation, currency, g.user["id"]),
            )
            db.commit()

            # Redirect to the generate route with the form data as URL parameters
            return redirect(
                url_for(
                    "pdf.generate_pdf",
                    first_name=first_name,
                    last_name=last_name,
                    country=country,
                    donation=donation,
                    currency=currency,
                )
            )

    return render_template("pdf/create.html")


def get_post(id, check_author=True):
    post = (
        get_db()
        .execute(
            "SELECT p.id, first_name, last_name, country, donation, currency, author_id"
            " FROM post p JOIN user u ON p.author_id = u.id"
            " WHERE p.id = ?",
            (id,),
        )
        .fetchone()
    )

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post["author_id"] != g.user["id"]:
        abort(403)

    return post


# Your route to generate the PDF
@bp.route("/generate_pdf", methods=["GET"])
def generate_pdf():
    # Retrieve form data from the URL parameters
    first_name = request.args.get("first_name")
    last_name = request.args.get("last_name")
    country = request.args.get("country")
    donation = request.args.get("donation")
    currency = request.args.get("currency")

    # Generate the PDF using reportlab with the retrieved form data
    pdf_buffer = generate_pdf_from_data(first_name, last_name, country, donation, currency)

    # Save the PDF to a temporary file
    cwd = pathlib.Path(__file__).parent
    pdf_file_path = cwd / f"naturelifecert_{first_name}_{last_name}.pdf"
    with open(pdf_file_path, "wb") as pdf_file:
        pdf_file.write(pdf_buffer)

    # Set the PDF file path as a response variable to access it in the after_request function
    response = make_response(redirect(url_for("index")))
    response.pdf_file_path = pdf_file_path

    return response


# Your route to initiate the PDF download
@bp.route("/download_pdf", methods=["GET"])
def download_pdf():
    # Get the file path of the generated PDF from the response variable
    pdf_file_path = request.response.pdf_file_path

    # Send the file as a response to initiate the download
    return send_file(pdf_file_path, as_attachment=True)


def generate_pdf_from_data(first_name, last_name, country, donation, currency):
    buffer = io.BytesIO()
    pdf_canvas = canvas.Canvas(buffer, pagesize=letter)

    # Add content to the PDF using the form data
    pdf_canvas.drawString(100, 700, "Form Data:")
    pdf_canvas.drawString(100, 680, f"First Name: {first_name}")
    pdf_canvas.drawString(100, 660, f"Last Name: {last_name}")
    pdf_canvas.drawString(100, 640, f"Country: {country}")
    pdf_canvas.drawString(100, 620, f"Donation: {donation}")
    pdf_canvas.drawString(100, 600, f"Currency: {currency}")
    # Add more content as needed

    # Save the PDF
    pdf_canvas.save()

    buffer.seek(0)
    return buffer.getvalue()


@bp.after_request
def handle_download_and_redirect(response):
    # Check if the response has a pdf_file_path attribute
    if hasattr(response, "pdf_file_path"):
        # Get the file path of the generated PDF from the response variable
        pdf_file_path = response.pdf_file_path

        # Send the file as a response to initiate the download
        response = send_file(pdf_file_path, as_attachment=True)

        #delete theh file
        pathlib.Path(response.pdf_file_path).unlink()

        # Redirect back to the index page after the PDF is downloaded
    return response
