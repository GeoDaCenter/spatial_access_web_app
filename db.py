from flask_sqlalchemy import SQLAlchemy
# from werkzeug import generate_password_hash, check_password_hash

import json

db = SQLAlchemy()

class User(db.Model):
	__tablename__ = 'users'
	email = db.Column(db.String(120), unique=True)
	
	def __init__(self, firstname, lastname, email, password):
		self.email = email.lower()
		
	