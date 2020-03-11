from flask import Flask, render_template, request, redirect, flash, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, BooleanField, SubmitField
from wtforms.validators import input_required, length, none_of
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import between, null
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import FlushError
from datetime import date, datetime, timedelta
import pandas as pd

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
    Metrics = db.relationship('Metric', backref='Server', lazy='dynamic')  # pseudo column for relationship
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
    ServerId = db.Column(db.Text, primary_key=True)  # primary key column
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
    ServerId = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


class MasterList(db.Model):  # Master list table
    __tablename__ = 'MasterList'
    __table_args__ = {'extend_existing': True}
    Type = db.Column(db.Text, primary_key=True)  # primary key column
    Name = db.Column(db.Text, primary_key=True)  # primary key column


# --------------------------------------------------------------------------------------------------------------------


class ChartForm(FlaskForm):  # form for the chart range
    startdate = StringField('start mm/dd/yyyy hh:mm:ss',
                            validators=[input_required(), length(min=10, max=19)])  # start date field
    enddate = StringField('end mm/dd/yyyy hh:mm:ss',
                          validators=[input_required(), length(min=10, max=19)])  # End date field

class MasterListForm(FlaskForm):
    type = SelectField('type', choices=[(st.TypeId, st.TypeName) for st in ServerType.query.all()],
                       validators=[input_required()])
    name = StringField('name', validators=[input_required()])
    add = SubmitField()


class HomeFilter(FlaskForm):
    filter = SelectField('filter', choices=[(st.TypeId, st.TypeName) for st in ServerType.query.all()],
                         # , ('', 'All')],
                         validators=[input_required()], )
    sub = SubmitField('Filter')


# ----------------------------------------------------------------------------------------------------------------------


date = date.today()  # gets today's date for use in default range for chart
today = date.strftime("%m/%d/%Y")  # reformat date to mm/dd/yyyy


# ----------------------------------------------------------------------------------------------------------------------
# Routes for the pages


@app.route('/', methods=['GET', 'POST'])  # this is whats at the end of the URL to get to the home page
@app.route('/home', methods=['GET', 'POST'])  # or this
def home():
    form = HomeFilter()
    server_table = Server.query.all()

    serverMetricsDict = {}  # Dictionary used for tooltips on home page
    for server in server_table:  # loop to add server id with its metrics to dictionary

        # gets metrics for each server in loop
        metric = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=server.ServerId).first()

        # creates key:value
        # key is server id, value is string of metrics as seen below
        serverMetricsDict[server.ServerID] = 'CPU: ' + str(metric.Cpu) + '%' + ' | RAM:' + str(metric.Ram) + '%' + \
                                             ' | Disk: ' + str(metric.Disk) + '%' + ' | GPU: ' + str(metric.Gpu) + '%' \
                                             + ' | Ping:' + str(metric.PingLatency) + 'ms'

    if form.validate_on_submit():
        server_table = Server.query.filter_by(
            ServerTypeID=form.filter.data)  # query that gets all of the servers in the Server table

    rack_table = Rack.query.filter(Rack.RackId == Server.RackID).order_by(
        Rack.Name)  # Show only racks that have servers on them

    masterList = []  # used to only display servers on the Master List
    for s in MasterList.query.all():
        masterList.append(s.num + '-' + s.Name)  # concatenates strings to make the server id
    print(masterList)

    return render_template('HomePageV2.html',
                           server=server_table, rack=rack_table, form=form, metric=serverMetricsDict,
                           masterList=masterList)  # returns V2 home page html doc with that variable


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/masterlist', methods=['GET', 'POST'])  # master list route
def master_list():
    form = MasterListForm()

    mList = MasterList.query.all()

    if form.validate_on_submit():
        mlType = ServerType.query.get(form.type.data)

        try:
            ML = MasterList(Type=mlType.TypeName, Name=form.name.data, num=form.type.data)
            db.session.add(ML)
            db.session.commit()
        except FlushError:
            db.session.rollback()
            print('Error 1234')
        print(form.name.data)
        print(form.type.data)
        print(mlType.TypeName)
        return redirect(url_for('master_list'))
    return render_template('MasterList.html', mList=mList, form=form)  # only returns the hard-coded master list for now


# ----------------------------------------------------------------------------------------------------------------------


@app.route("/masterlist/<mlType>&<mlName>/delete", methods=['POST'])
def deleteServer(mlType, mlName):
    print(mlName)
    print(mlType)
    tmp = MasterList.query.get_or_404((mlType, mlName))
    print(tmp.Type)
    print(tmp.Name)
    print(tmp.num)

    db.session.delete(tmp)
    db.session.commit()
    flash('The Server has been deleted!', 'success')
    return redirect(url_for('master_list'))


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/real-time-data-overview/<slug>')  # route for the realtime data overview for a specific server
def RT(slug):  # Slug is the Server Id
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    services = Service.query.filter_by(ServerId=slug)  # query for the services on this server

    databases = Database.query.filter_by(ServerId=slug)  # query for the databases on this server

    runningjobs = RunningJob.query.filter_by(ServerId=slug)  # query for the runningjobs on this server

    tmpLoc = Server.query.filter_by(ServerId=slug).first()

    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()

    tmpLoc3 = Location.query.filter_by(LocationId=tmpLoc2.LocationId).first()

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    if metric_row.PingLatency != null:
        status = "Responding"
    else:
        status = "Not Responding"

    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_row, service=services,
                           database=databases, runningjob=runningjobs, location=tmpLoc3, rack=tmpLoc2, status=status)
    #   returns the template for real time data overview with ^ variables passed to it


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def CPU(slug):  # Slug is the Server Id
    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '08/31/2019 23:50:00', '09/01/2019 23:50:00'))]

    # gets all cpu usages for this server between dates
    useRange = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '08/31/2019 23:50:00', '09/01/2019 23:50:00'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # converts inputted string to date or datetime
        try:
            sDate = datetime.strptime(startdate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            sDate = datetime.strptime(startdate, '%m/%d/%Y')
        try:
            eDate = datetime.strptime(enddate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            eDate = datetime.strptime(enddate, '%m/%d/%Y')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

        else:  # if deference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.Cpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Cpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Cpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    dateRange.append(x.date().strftime('%m/%d/%Y'))  # reformats x and adds it to date list
                    averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                    minList.append(min)  # adds min to list
                    maxList.append(max)  # adds MAX to list

                    x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    # return for default date range
    return render_template('Usage-CPUTemp.html', server=server, ametric=tmp, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Disk/<slug>', methods=['POST', 'GET'])  # route for Disk usage for a specific server
def disk(slug):  # Slug is the Server Id

    # gets all disk usages for this server between dates
    # diskUse = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    # gets all Disk usages for this server between dates
    useRange = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    partAUse = [metrics.PartA for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]
    partBUse = [metrics.PartB for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]
    partCUse = [metrics.PartC for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]
    partDUse = [metrics.PartD for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # converts inputted string to date or datetime
        try:
            sDate = datetime.strptime(startdate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            sDate = datetime.strptime(startdate, '%m/%d/%Y')
        try:
            eDate = datetime.strptime(enddate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            eDate = datetime.strptime(enddate, '%m/%d/%Y')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

        else:  # if deference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    dateRange.append(x.date().strftime('%m/%d/%Y'))  # reformat x and adds it to date list
                    averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                    minList.append(min)  # adds min to list
                    maxList.append(max)  # adds MAX to list

                    x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    # return for default date range
    return render_template('Usage-Disk.html', server=server, ametric=tmp, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, aUsage=partAUse,
                           bUsage=partBUse, cUsage=partCUse, dUsage=partDUse)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-GPU/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def gpu(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    # gets all Gpu usages for this server between dates
    useRange = [metrics.Gpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # converts inputted string to date or datetime
        try:
            sDate = datetime.strptime(startdate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            sDate = datetime.strptime(startdate, '%m/%d/%Y')
        try:
            eDate = datetime.strptime(enddate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            eDate = datetime.strptime(enddate, '%m/%d/%Y')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.Gpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

        else:  # if deference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.Gpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Gpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Gpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    dateRange.append(x.date().strftime('%m/%d/%Y'))  # reformat x and adds it to date list
                    averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                    minList.append(min)  # adds min to list
                    maxList.append(max)  # adds MAX to list

                    x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    # return for default date range
    return render_template('Usage-GPU.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-RAM/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ram(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    # gets all Ram usages for this server between dates
    useRange = [metrics.Ram for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # converts inputted string to date or datetime
        try:
            sDate = datetime.strptime(startdate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            sDate = datetime.strptime(startdate, '%m/%d/%Y')
        try:
            eDate = datetime.strptime(enddate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            eDate = datetime.strptime(enddate, '%m/%d/%Y')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.Ram for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

        else:  # if deference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.Ram).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Ram).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Ram).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    dateRange.append(x.date().strftime('%m/%d/%Y'))  # reformat x and adds it to date list
                    averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                    minList.append(min)  # adds min to list
                    maxList.append(max)  # adds MAX to list

                    x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    # return for default date range
    return render_template('Usage-RAM.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Ping/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ping(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackID).first()  # gets rack for this server

    if metric_row.PingLatency != null:  # checks to see if ping is responding
        status = "Responding"
    else:
        status = "Not Responding"

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    # gets all Ping usages for this server between dates
    useRange = [metrics.PingLatency for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, '09/01/2019 11:50:00', '09/01/2019 23:50:00'))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        startdate = form.startdate.data  # gets start and end date from form
        enddate = form.enddate.data

        # converts inputted string to date or datetime
        try:
            sDate = datetime.strptime(startdate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            sDate = datetime.strptime(startdate, '%m/%d/%Y')
        try:
            eDate = datetime.strptime(enddate, '%m/%d/%Y %H:%M:%S')
        except ValueError:
            eDate = datetime.strptime(enddate, '%m/%d/%Y')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.PingLatency for metrics in
                        Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                            between(Metric.Time, startdate, enddate))]

        else:  # if deference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.PingLatency).label('average')).order_by(
                        Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.PingLatency).label('average')).order_by(
                        Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.PingLatency).label('average')).order_by(
                        Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%m/%d/%Y'), z.strftime('%m/%d/%Y'))).scalar()

                    dateRange.append(x.date().strftime('%m/%d/%Y'))  # reformat x and adds it to date list
                    averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                    minList.append(min)  # adds min to list
                    maxList.append(max)  # adds MAX to list

                    x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    # return for default date range
    return render_template('Usage-Ping.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, status=status)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':  # something for flask
    app.run(debug=True)
