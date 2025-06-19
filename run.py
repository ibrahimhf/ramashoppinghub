from app import create_app, db  # make sure to import db from your app package
from flask_migrate import Migrate

app = create_app()  # first create the app
migrate = Migrate(app, db)  # then initialize migrate with app and db

if __name__ == '__main__':
    app.run(debug=True)