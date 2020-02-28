from flask import Flask, render_template, request
from flask_wtf import Form
from wtforms import StringField, DateField
from wtforms.validators import input_required, length
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import between
from datetime import date

app = Flask(__name__)  # something for flask
app.jinja_env.globals.update(zip=zip)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///StubServersDB_V4.db'  # sets the DB to the stubDB

app.config['SECRET_KEY'] = 'secret ssmt'  # secret key used for by WTforms for forms

db = SQLAlchemy(app)  # something SQL Alchemy needs
db.Model.metadata.reflect(db.engine)  # Allows SQL alchemy to look into the DB for info on the tables


# -----------------------------------------------------------------------------------------------------------
# Tables for SQL alchemy


class Server(db.Model):  # Server Table
    __tablename__ = 'Server'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)  # primary key column
    Metrics = db.relationship('Metric', backref='Server', lazy=True)  # pseudo column for relationship
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))  # foreign key column? **********************


class Metric(db.Model):  # metric table
    __tablename__ = 'Metric'
    __table_args__ = {'extend_existing': True}
    MetricId = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))  # foreign key column
    # Time = db.column(db.DATETIME)


class Rack(db.Model):  # Rack table
    __tablename__ = 'Rack'
    __table_args__ = {'extend_existing': True}
    RackId = db.Column(db.Text, primary_key=True)  # primary key column
    LocationId = db.Column(db.Text, db.ForeignKey('location.LocationId'))  # foreign key column


class Location(db.Model):  # Location Table
    __tablename__ = 'Location'
    __table_args__ = {'extend_existing': True}
    LocationId = db.Column(db.Text, primary_key=True)  # primary key column


class Database(db.Model):  # Databases table
    __tablename__ = 'Database'
    __table_args__ = {'extend_existing': True}
    DatabaseId = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


class RunningJob(db.Model):  # Running jobs table
    __tablename__ = 'RunningJob'
    __table_args__ = {'extend_existing': True}
    ServerId = db.Column(db.Text, primary_key=True)  # primary key column
    JobName = db.Column(db.Text, primary_key=True)  # primary key column
    StartTime = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


class ServerType(db.Model):  # Server Type table
    __tablename__ = 'ServerType'
    __table_args__ = {'extend_existing': True}
    TypeId = db.Column(db.Text, primary_key=True)  # primary key column


class Service(db.Model):  # Service table
    __tablename__ = 'Service'
    __table_args__ = {'extend_existing': True}
    ServiceId = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


class MasterList(db.Model):  # Master list table
    __tablename__ = 'MasterList'
    __table_args__ = {'extend_existing': True}
    Type = db.Column(db.Text, primary_key=True)  # primary key column
    Name = db.Column(db.Text, primary_key=True)  # primary key column


# --------------------------------------------------------------------------------------------------------------------


class ChartForm(Form):  # form for the chart range
    startdate = StringField('startdate', validators=[input_required(), length(min=10, max=10)])  # start date field
    enddate = StringField('enddate', validators=[input_required(), length(min=10, max=10)])  # End date field

# ----------------------------------------------------------------------------------------------------------------------


date = date.today()  # gets today's date for use in default range for chart
today = date.strftime("%m/%d/%Y")  # reformat date to mm/dd/yyyy

# ----------------------------------------------------------------------------------------------------------------------
# Routes for the pages


@app.route('/')  # this is whats at the end of the URL to get to the home page
@app.route('/home')  # or this
def home():
    server_table = Server.query.all()  # query that gets all of the servers in the Server table
    rack_table = Rack.query.all()

    # for r in rack_table:
    #     for s in server_table:
    #         if s.RackID == r.RackID:
    #             print(s.Name)
    #     print(r.Name)

    return render_template('HomePageV2.html', server=server_table, rack=rack_table)  # returns V2 home page html doc with that variable
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/masterlist')  # master list route
def master_list():
    return render_template('MasterList.html')  # only returns the hard-coded master list for now
# ----------------------------------------------------------------------------------------------------------------------


# @app.route('/real-time-data-overview')    **** this is the route for the hard coded Real time Data Overview ****
# def RTDO():
#     return render_template('RealTimeDataOverview.html')
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/real-time-data-overview/<slug>')  # route for the realtime data overview for a specific server
def RT(slug):  # Slug is the Server Id
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    services = Service.query.filter_by(ServerId=slug)  # query for the services on this server

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_row, service=services)
    #   returns the template for real time data overview with ^ variables passed to it
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def CPU(slug):  # Slug is the Server Id
    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # gets all dates for this server between dates
    cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    # gets all cpu usages for this server between dates
    cpuUse = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # Returns list of dates within start and end date
        dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # Returns usages that within  start and end date
        useRange = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # return for if user provides input
        return render_template('Usage-CPUTemp.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                               form=form)
    # return for default date range
    return render_template('Usage-CPUTemp.html', server=server, ametric=metric_row, date=cpuDate, usage=cpuUse,
                           form=form)
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Disk/<slug>', methods=['POST', 'GET'])  # route for Disk usage for a specific server
def disk(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # gets all dates for this server between dates
    cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    # gets all disk usages for this server between dates
    diskUse = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # Returns list of dates within start and end date
        dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # Returns usages that within  start and end date
        useRange = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # return for if user provides input
        return render_template('Usage-Disk.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                               form=form)
    # return for default date range
    return render_template('Usage-Disk.html', server=server, ametric=metric_row, date=cpuDate, usage=diskUse,
                           form=form)
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-GPU/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def gpu(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # gets all dates for this server between dates
    cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    # gets all disk usages for this server between dates
    gpuUse = [metrics.Gpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # Returns list of dates within start and end date
        dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # Returns usages that within  start and end date
        useRange = [metrics.Gpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # return for if user provides input
        return render_template('Usage-GPUTemp.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                               form=form)
    # return for default date range
    return render_template('Usage-GPU.html', server=server, ametric=metric_row, date=cpuDate, usage=gpuUse,
                           form=form)
# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-RAM/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ram(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # gets all dates for this server between dates
    cpuDate = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    # gets all disk usages for this server between dates
    ramUse = [metrics.Ram for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '07/06/2019', '07/07/2019'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # Returns list of dates within start and end date
        dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # Returns usages that within  start and end date
        useRange = [metrics.Ram for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
            between(Metric.Time, startdate, enddate))]

        # return for if user provides input
        return render_template('Usage-RAM.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                               form=form)
    # return for default date range
    return render_template('Usage-RAM.html', server=server, ametric=metric_row, date=cpuDate, usage=ramUse,
                           form=form)

# @app.route('/usage-cpu')     *** THIS IS THE ROUTE FOR THE HARD-CODED CPU USAGE PAGE ***
# def usage_CPU():
#     return render_template('Usage-CPU.html')


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':  # something for flask
    app.run()
