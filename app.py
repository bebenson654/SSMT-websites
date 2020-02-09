from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import json

# with open('Db-01.json') as f:
#     datas = json.load(f)


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///StubServersDB.db'
db = SQLAlchemy(app)

db.Model.metadata.reflect(db.engine)


class Server(db.Model):
    __tablename__ = 'Server'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)


# 5:30 of video 2 importing data (JSON)
''' 
7:40 of vid 2 code block (for loop) - 
    {% for post in posts %} 
        <h1>{{ post.title }} </h1>
    {% end for %}
'''


@app.route('/')
@app.route('/home')
def home():
    print("Total number of servers is: ", Server.query.count())
    return render_template('HomePage.html')


@app.route('/masterlist')
def master_list():
    return render_template('MasterList.html')


@app.route('/real-time-data-overview')
def RTDO():
    return render_template('RealTimeDataOverview.html')


@app.route('/usage-cpu')
def usage_CPU():
    return render_template('Usage-CPU.html')


# @app.route('/' + str(datas.ServerName).lower() + '-rt')
# def RTDO():
#     return render_template('RealTimeDataOverview.html', datas=datas)


if __name__ == '__main__':
    app.run()
