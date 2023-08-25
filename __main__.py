from passlib.hash import bcrypt
from jobwarden.app import app, db
from datetime import datetime

if __name__ == "__main__":
    # create admin if no admin user exists
    admins = db.get_admins()
    if len(admins) == 0:
        print(
            "Creating default admin employee. Be sure to delete this when you create your admin account"
        )
        db.create_employee(
            "Admin", "admin@jobwarden.com", bcrypt.hash("admin123"), "ADMIN"
        )

    customers = db.get_customer_names()
    if len(customers) == 0:
        print("Creating default customer. Be sure to delete this.")
        db.create_customer(
            "Default Customer",
            "customer@example.com",
            "5012015555",
            "1234567890",
            datetime(2023, 8, 25),
        )
    app.run(debug=True)
