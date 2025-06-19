class Config:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///invoices.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'your-secret-key'