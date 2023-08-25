from datetime import datetime

import enum

from sqlalchemy import (
    DECIMAL,
    Column,
    ForeignKey,
    Integer,
    String,
    create_engine,
    Enum,
    Boolean,
    func,
    DateTime,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from jobwarden.app import app

Base = declarative_base()


class Rank(enum.Enum):
    REGULAR = 0
    MANAGER = 1
    ADMIN = 2


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=True)
    phone = Column(Integer, nullable=True)
    license_number = Column(Integer, nullable=False)
    birthdate = Column(DateTime)
    dt_created = Column(DateTime(timezone=True), server_default=func.now())
    dt_updated = Column(DateTime(timezone=True), server_default=func.now())

    jobs = relationship("Job")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, nullable=False)
    part_no = Column(String, nullable=False)
    link = Column(String, nullable=False)
    cost = Column(DECIMAL(scale=2), nullable=True)
    in_stock = Column(Boolean, nullable=False)
    jcn = Column(Integer, ForeignKey("jobs.jcn"))
    dt_created = Column(DateTime(timezone=True), server_default=func.now())
    dt_updated = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="orders")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, nullable=False)
    jcn = Column(
        Integer, nullable=False
    )  # job control number (julian date + increment)
    customer_id = Column(Integer, ForeignKey("customers.id"))
    dt_created = Column(DateTime(timezone=True), server_default=func.now())
    dt_updated = Column(DateTime(timezone=True), server_default=func.now())

    customer = relationship("Customer", back_populates="jobs")
    orders = relationship("Order", back_populates="job")


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String(length=255), unique=True, nullable=True)
    username = Column(String(length=32), unique=True, nullable=True)
    password = Column(String(length=255), unique=False, nullable=False)
    rank = Column(Enum(*list(Rank.__members__)), default=list(Rank.__members__)[0])
    dt_created = Column(DateTime(timezone=True), server_default=func.now())


class EmployeeApplicant(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String(length=255), unique=True, nullable=True)
    username = Column(String(length=32), unique=True, nullable=True)
    password = Column(String(length=255), unique=False, nullable=False)
    dt_created = Column(DateTime(timezone=True), server_default=func.now())


class Login(Base):
    __tablename__ = "logins"

    id = Column(Integer, primary_key=True, nullable=False)
    userid = Column(Integer, ForeignKey("employees.id"), nullable=False)
    username = Column(String(length=32), nullable=False)
    rank = Column(Integer, ForeignKey("employees.rank"), unique=False, nullable=True)
    login_dt = Column(DateTime(timezone=True), server_default=func.now())


class Database:
    def __init__(self):
        self.engine = create_engine(
            f"sqlite:///{app.config['DATABASE_FILE']}?check_same_thread=False",
            echo=False,
        )
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()
        Base.metadata.create_all(self.engine)

    def get_admins(self):
        return self.session.query(Employee.username).filter_by(rank="ADMIN").all()

    def get_username(self, userid):
        if userid is not None:
            try:
                return (
                    self.session.query(Employee.username).filter_by(id=userid).first()
                )
            except Exception as e:
                print(f"User does not exist for id {userid}", e)
        else:
            print("Cannot get username for userid 'None'", userid)
            return False

    def get_password(self, username):
        try:
            # get user data using email
            id, password = (
                self.session.query(Employee.id, Employee.password)
                .filter_by(username=username)
                .all()[0]
            )

            # return the id as well as the encoded password hash and salt ready for hashing and verifying
            return (id, password)
        except Exception as e:
            # something happened. Oh well.
            print(e)
            return (None, None)

    def check_user_exists(self, username, email):
        # check username does not exist
        q = self.session.query(Employee.username).filter_by(username=username).all()
        if len(q) != 0:
            return True
        # check email does not exist
        q = self.session.query(Employee.email).filter_by(email=email).all()
        if len(q) != 0:
            return True
        return False

    def create_employee(self, username, email, pwd_hash, rank):
        if not self.check_user_exists(username, email):
            try:
                self.session.add(
                    Employee(
                        email=email, username=username, password=pwd_hash, rank=rank
                    )
                )
                self.session.commit()
            except Exception as e:
                print("Error occurred creating employee.\n", e)
                return False

    def create_applicant(self, username, email, pwd_hash):
        if not self.check_user_exists(username, email):
            try:
                self.session.add(
                    EmployeeApplicant(email=email, username=username, password=pwd_hash)
                )
                self.session.commit()
                return True
            except Exception as e:
                print("Error occurred creating application.\n", e)
                return False

    def check_is_admin(self, userid):
        try:
            q = self.session.query(Employee.rank).filter_by(id=userid).first()
            if q[0] == "ADMIN":
                print("user is admin")
                return True
            else:
                return False
        except Exception as e:
            print(f"An error occurred while checking is_admin: {userid}", e)
            return False

    def get_applications(self):
        try:
            q = self.session.query(
                EmployeeApplicant.username, EmployeeApplicant.email
            ).all()
            return q
        except Exception as e:
            print("An error occurred while getting applications", e)

    def get_all_users(self):
        try:
            q = self.session.query(Employee.username, Employee.rank, Employee.id).all()
            return q
        except Exception as e:
            print("An error occurred while getting employees", e)

    def create_login(self, userid):
        try:
            # get the employee
            user = (
                self.session.query(Employee.username, Employee.rank)
                .filter_by(id=userid)
                .first()
            )
        except Exception as e:
            print("An error occurred while getting employees", e)
            return

        now = datetime.now()

        try:
            # create login entry
            self.session.add(
                Login(userid=userid, username=user[0], rank=user[1], login_dt=now)
            )
            self.session.commit()
            return True
        except Exception as e:
            print("An error occurred while adding login", e)
            return False

    def get_logins(self):
        return (
            self.session.query(Login.username, Login.rank, Login.login_dt)
            .order_by(-Login.id)
            .limit(10)
            .all()
        )

    def approve_applicant(self, username, email):
        applicant = (
            self.session.query(EmployeeApplicant)
            .filter_by(email=email, username=username)
            .first()
        )
        if not self.check_user_exists(applicant.username, applicant.email):
            self.session.add(
                Employee(
                    email=applicant.email,
                    username=applicant.username,
                    password=applicant.password,
                )
            )
        self.session.delete(applicant)
        self.session.commit()

    def reject_applicant(self, username, email):
        self.session.query(EmployeeApplicant).filter_by(
            email=email, username=username
        ).delete()
        self.session.commit()

    def change_rank(self, userid, new_rank):
        try:
            user = self.session.query(Employee).filter_by(id=userid).first()
            user.rank = new_rank.upper()
            self.session.commit()
            return True
        except Exception as e:
            print(
                f"An error occurred while changing user ({userid}) rank to {new_rank}",
                e,
            )
            return False

    def get_customer_names(self):
        try:
            customers = self.session.query(Customer).all()
            return customers
        except Exception as e:
            print(f"An error occurred while getting all customers", e)
            return False

    def create_customer(self, name, email, phone, license_number, bday):
        try:
            customer = Customer(
                name=name,
                email=email,
                phone=phone,
                license_number=license_number,
                birthdate=bday,
            )
            self.session.add(customer)
            self.session.commit()
        except Exception as e:
            print(f"An error occurred creating a new customer {e}")
