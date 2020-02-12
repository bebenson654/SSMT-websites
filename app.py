from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import json


app = Flask(__name__)


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///StubServersDB.db'
db = SQLAlchemy(app)

db.Model.metadata.reflect(db.engine)


class Server(db.Model):
    __tablename__ = 'Server'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)
    Metrics = db.relationship('Metric', backref='Server', lazy=True)


class Metric(db.Model):
    __tablename__ = 'Metric'
    __table_args__ = {'extend_existing': True}
    MetricId = db.Column(db.Text, primary_key=True)
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))  # ,nullable=False)


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
    server_table = Server.query.all()
    # print("Total number of servers is: ", Server.query.count())
    return render_template('HomePage.html', server=server_table)


@app.route('/masterlist')
def master_list():
    return render_template('MasterList.html')


@app.route('/real-time-data-overview')
def RTDO():
    return render_template('RealTimeDataOverview.html')


@app.route('/real-time-data-overview/<slug>')
def RT(slug):
    # print(Server.query.join(Metric, Metric.ServerID == Server.ServerId).Cpu)
    # records = session.query(Customer).join(Order, Order.customer_id == Customer.id).all()
    # metric = Metric.query.filter(Metric.ServerID == Server.ServerId)

    server = Server.query.filter_by(ServerId=slug).first()
    print(slug)
    # peter = User.query.filter_by(username='peter').first()
    # peter.id
    tmp = Metric.query.filter_by(ServerID=slug).scalar()
    print(tmp.MetricId)
    metric_table = Metric.query.get(
        tmp.MetricId)  # Metric.query.filter(Metric.ServerID == Server.ServerId).max(Metric.Time)
    # cpu = Metric.Cpu.query.filter_by(ServerID=slug)

    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_table)


@app.route('/usage-cpu')
def usage_CPU():
    return render_template('Usage-CPU.html')


# @app.route('/' + str(datas.ServerName).lower() + '-rt')
# def RTDO():
#     return render_template('RealTimeDataOverview.html', datas=datas)


if __name__ == '__main__':
    app.run()
