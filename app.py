from flask import Flask, render_template, request
from flask_wtf import Form
from wtforms import StringField, DateField
from wtforms.validators import input_required
from flask_sqlalchemy import SQLAlchemy
import json

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///StubServersDB_V2.db'
app.config['SECRET_KEY'] = 'secret ssmt'
db = SQLAlchemy(app)

db.Model.metadata.reflect(db.engine)


class Server(db.Model):
    __tablename__ = 'Server'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)
    Metrics = db.relationship('Metric', backref='Server', lazy=True)
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))


class Metric(db.Model):
    __tablename__ = 'Metric'
    __table_args__ = {'extend_existing': True}
    MetricId = db.Column(db.Text, primary_key=True)
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))  # ,nullable=False)


class Rack(db.Model):
    __tablename__ = 'Rack'
    __table_args__ = {'extend_existing': True}
    RackId = db.Column(db.Text, primary_key=True)
    LocationId = db.Column(db.Text, db.ForeignKey('location.LocationId'))


class Location(db.Model):
    __tablename__ = 'Location'
    __table_args__ = {'extend_existing': True}
    LocationId = db.Column(db.Text, primary_key=True)


class Database(db.Model):
    __tablename__ = 'Database'
    __table_args__ = {'extend_existing': True}
    DatabaseId = db.Column(db.Text, primary_key=True)
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))


class RunningJob(db.Model):
    __tablename__ = 'RunningJob'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)
    JobName = db.Column(db.Text, primary_key=True)
    StartTime = db.Column(db.Text, primary_key=True)
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))


class ServerType(db.Model):
    __tablename__ = 'ServerType'
    __table_args__ = {'extend_existing': True}
    TypeId = db.Column(db.Text, primary_key=True)


class Service(db.Model):
    __tablename__ = 'Service'
    __table_args__ = {'extend_existing': True}
    ServiceId = db.Column(db.Text, primary_key=True)
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))


class MasterList(db.Model):
    __tablename__ = 'MasterList'
    __table_args__ = {'extend_existing': True}
    Type = db.Column(db.Text, primary_key=True)
    Name = db.Column(db.Text, primary_key=True)


class ChartForm(Form):
    startdate = StringField('startdate', validators=[input_required()])
    enddate = StringField('enddate', validators=[input_required()])


@app.route('/')
@app.route('/home')
def home():
    # rack_table = Rack.query.all()

    server_table = Server.query.all()
    return render_template('HomePageV2.html', server=server_table)  # , rack=rack_table)


@app.route('/masterlist')
def master_list():
    return render_template('MasterList.html')


# @app.route('/real-time-data-overview')
# def RTDO():
#     return render_template('RealTimeDataOverview.html')


@app.route('/real-time-data-overview/<slug>')
def RT(slug):
    server = Server.query.filter_by(ServerId=slug).first()

    services = Service.query.filter_by(ServerId=slug)

    tmp = Metric.query.order_by(Metric.Time).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)
    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_row, service=services)


@app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])
def CPU(slug):
    form = ChartForm()
    server = Server.query.filter_by(ServerId=slug).first()

    tmp = Metric.query.order_by(Metric.Time).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)

    cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug)]
    cpuUse = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug)]

    if form.validate_on_submit():
        cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug)]
        cpuUse = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug)]

    return render_template('Usage-CPUTemp.html', server=server, ametric=metric_row, date=cpuDate, usage=cpuUse, form=form)


# @app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])
# def CPU_post(slug):
#     server = Server.query.filter_by(ServerId=slug).first()
#
#     tmp = Metric.query.order_by(Metric.Time).filter_by(ServerID=slug).first()
#     metric_row = Metric.query.get(tmp.MetricId)
#
#     cpuUse = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug)]

    # sdate = request.form['start date']
    # edate = request.form['end date']
    # cpuDate = [metrics.Time for metrics in
    #            Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).between(Metric.Time, sdate, edate)]


# @app.route('/usage-cpu')
# def usage_CPU():
#     return render_template('Usage-CPU.html')


if __name__ == '__main__':
    app.run()
