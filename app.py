from flask import Flask, render_template, request, redirect, flash, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, Field
from wtforms.validators import input_required, length
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import between, null
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import FlushError
from datetime import date, datetime, timedelta
import pandas as pd
from wtforms.fields.html5 import DateTimeLocalField
from flask_fontawesome import FontAwesome
from _collections import defaultdict
from itertools import zip_longest

app = Flask(__name__)  # something for flask
app._static_folder = 'static'
app.jinja_env.globals.update(zip=zip, zip_longest=zip_longest)
fa = FontAwesome(app)

app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'sqlite:///NewDatabase1.db'  # sets the DB to the stubDB

app.config[
    'SECRET_KEY'] = 'secret ssmt'  # secret key used for by WTforms for forms

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


class Partition(db.Model):  # Master list table
    __tablename__ = 'Partition'
    __table_args__ = {'extend_existing': True}
    PartitionId = db.Column(db.Text, primary_key=True)  # primary key column
    Time = db.Column(db.Text, primary_key=True)
    ServerId = db.Column(db.Text, primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


# --------------------------------------------------------------------------------------------------------------------


mDate = Metric.query.order_by(Metric.Time.desc()).first()  # gets most recent row from metric

maxDate = mDate.Time  # grabs time from row above^

maxDateMinus12 = datetime.strptime(maxDate, '%Y-%m-%d %H:%M:%S')  # converts it to date time object
maxDateMinus12 = maxDateMinus12 - timedelta(hours=12)  # subtracts 12 hrs
maxDateMinus12 = datetime.strftime(maxDateMinus12, '%Y-%m-%d %H:%M:%S')  # converts back to string


# ----------------------------------------------------------------------------------------------------------------------

class ChartForm(FlaskForm):  # form for the chart range
    defStartDate = datetime.strptime(maxDateMinus12, '%Y-%m-%d %H:%M:%S')
    defEndDate = datetime.strptime(maxDate, '%Y-%m-%d %H:%M:%S')
    startdate = DateTimeLocalField(defStartDate, format='%Y-%m-%dT%H:%M')
    enddate = DateTimeLocalField(defEndDate, format='%Y-%m-%dT%H:%M')


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


# Routes for the pages


@app.route('/', methods=['GET', 'POST'])  # this is whats at the end of the URL to get to the home page
@app.route('/home', methods=['GET', 'POST'])  # or this
def home():
    form = HomeFilter()
    server_table = Server.query.all()

    serverMetricsDict = {}  # Dictionary used for tooltips on home page

    serverColorDict = {}  # Dictionary used for Color coding on home page

    for server in server_table:  # loop to add server id with its metrics to dictionary

        # gets metrics for each server in loop
        metric = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=server.ServerId).first()

        # sets color server in card
        if metric.Cpu > 80 or metric.Disk > 90 or metric.Ram > 80 \
                or metric.Gpu > 90 or metric.PingLatency is None:
            color = 'danger'  # bootstrap Red
            icon = 'times'  # # Font Awesome icon 'x'

        elif 50 <= metric.Cpu <= 80 or 70 <= metric.Disk <= 90 or \
                50 <= metric.Ram <= 80 or 50 <= metric.Gpu <= 80:
            color = 'warning'  # bootstrap Yellowish
            icon = 'exclamation-triangle'  # # Font Awesome icon warning triangle

        elif metric.Cpu < 50 or metric.Disk < 70 or metric.Ram < \
                50 or metric.Gpu < 50 or metric.PingLatency is not None:
            color = 'success'  # bootstrap Green
            icon = 'check'  # # Font Awesome icon check

        else:
            color = 'light'  # bootstrap White
            icon = 'question'  # Font Awesome icon '?'

        serverColorDict[server.ServerID + 'color'] = color  # sets server color to color assigned above
        serverColorDict[server.ServerID + 'icon'] = icon  # sets server icon to color assigned above

        # creates key:value for tool tips
        # key is server id, value is string of metrics as seen below
        serverMetricsDict[server.ServerID] = 'CPU: ' + str(metric.Cpu) + '%' + ' | RAM:' + str(metric.Ram) + '%' + \
                                             ' | Disk: ' + str(metric.Disk) + '%' + ' | GPU: ' + str(metric.Gpu) + '%' \
                                             + ' | Ping:' + str(metric.PingLatency) + 'ms'

    if form.validate_on_submit():
        server_table = Server.query.filter_by(
            ServerTypeId=form.filter.data)  # query that gets all of the servers in the Server table

    masterList = []  # used to only display servers on the Master List
    for s in MasterList.query.all():
        masterList.append(s.Num + '-' + s.Name)  # concatenates strings to make the server id

    rack_table = Rack.query.filter(Rack.RackId == Server.RackId).order_by(
        Rack.Name)  # Show only racks that have servers on them

    return render_template('HomePageV2.html',
                           server=server_table, rack=rack_table, form=form, metric=serverMetricsDict,
                           masterList=masterList,
                           color=serverColorDict)  # returns V2 home page html doc with that variable


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/masterlist', methods=['GET', 'POST'])  # master list route
def master_list():
    form = MasterListForm()

    mList = MasterList.query.all()

    if form.validate_on_submit():
        mlType = ServerType.query.get(form.type.data)

        try:
            ML = MasterList(Type=mlType.TypeName, Name=form.name.data, Num=form.type.data)
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
    print(tmp.Num)

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

    testRJ = RunningJob.query.filter_by(ServerId=slug).first()  # hides running job table when empty
    if testRJ is None:
        runningjobs = 0
    testDB = Database.query.filter_by(ServerId=slug).first()  # hided DB table when empty
    if testDB is None:
        databases = 0

    tmpLoc = Server.query.filter_by(ServerId=slug).first()

    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()

    tmpLoc3 = Location.query.filter_by(LocationId=tmpLoc2.LocationId).first()

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    serverColorDict = {}  # used to to get color and icon for conditional formatting

    if metric_row.Cpu > 80:
        serverColorDict['CpuColor'] = 'danger'  # sets color to bootstrap red
        serverColorDict['CpuIcon'] = 'times'  # sets icon to Font Awesome 'x'
    elif 50 <= metric_row.Cpu <= 80:
        serverColorDict['CpuColor'] = 'warning'  # sets color to bootstrap yellowish
        serverColorDict['CpuIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
    elif metric_row.Cpu < 50:
        serverColorDict['CpuColor'] = 'success'  # sets color to bootstrap green
        serverColorDict['CpuIcon'] = 'check'  # sets icon to Font Awesome check
    else:
        serverColorDict['CpuColor'] = 'dark'  # sets color to bootstrap black
        serverColorDict['CpuIcon'] = 'question'  # sets icon to Font Awesome '?'

    if metric_row.Gpu > 80:
        serverColorDict['GpuColor'] = 'danger'  # sets color to bootstrap red
        serverColorDict['GpuIcon'] = 'times'  # sets icon to Font Awesome 'x'
    elif 50 <= metric_row.Gpu <= 80:
        serverColorDict['GpuColor'] = 'warning'  # sets color to bootstrap yellowish
        serverColorDict['GpuIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
    elif metric_row.Gpu < 50:
        serverColorDict['GpuColor'] = 'success'  # sets color to bootstrap green
        serverColorDict['GpuIcon'] = 'check'  # sets icon to Font Awesome check
    else:
        serverColorDict['GpuColor'] = 'dark'  # sets color to bootstrap black
        serverColorDict['GpuIcon'] = 'question'  # sets icon to Font Awesome '?'

    if metric_row.Ram > 80:
        serverColorDict['RamColor'] = 'danger'  # sets color to bootstrap red
        serverColorDict['RamIcon'] = 'times'  # sets icon to Font Awesome 'x'
    elif 50 <= metric_row.Ram <= 80:
        serverColorDict['RamColor'] = 'warning'  # sets color to bootstrap yellowish
        serverColorDict['RamIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
    elif metric_row.Ram < 50:
        serverColorDict['RamColor'] = 'success'  # sets color to bootstrap green
        serverColorDict['RamIcon'] = 'check'  # sets icon to Font Awesome check
    else:
        serverColorDict['RamColor'] = 'dark'  # sets color to bootstrap black
        serverColorDict['RamIcon'] = 'question'  # sets icon to Font Awesome '?'

    if metric_row.Disk > 90:
        serverColorDict['DiskColor'] = 'danger'  # sets color to bootstrap red
        serverColorDict['DiskIcon'] = 'times'  # sets icon to Font Awesome 'x'
    elif 70 <= metric_row.Disk <= 90:
        serverColorDict['DiskColor'] = 'warning'  # sets color to bootstrap yellowish
        serverColorDict['DiskIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
    elif metric_row.Disk < 70:
        serverColorDict['DiskColor'] = 'success'  # sets color to bootstrap green
        serverColorDict['DiskIcon'] = 'check'  # sets icon to Font Awesome check
    else:
        serverColorDict['Disk'] = 'dark'  # sets color to bootstrap black
        serverColorDict['DiskIcon'] = 'question'  # sets icon to Font Awesome '?'

    if metric_row.PingLatency != null:
        status = "Responding"  # sets status of ping
        serverColorDict['PingColor'] = 'success'  # sets color to bootstrap green
        serverColorDict['PingIcon'] = 'check'  # sets icon to Font Awesome check
    elif metric_row.PingLatency == null:
        status = "Not Responding"  # sets status of ping
        serverColorDict['PingColor'] = 'danger'  # sets color to bootstrap red
        serverColorDict['PingIcon'] = 'times'  # sets icon to Font Awesome 'x'
    else:
        status = "Unknown"  # sets status of ping
        serverColorDict['PingColor'] = 'dark'  # sets color to bootstrap black
        serverColorDict['PingIcon'] = 'question'  # sets icon to Font Awesome '?'

    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_row, service=services,
                           database=databases, runningjob=runningjobs, location=tmpLoc3, rack=tmpLoc2, status=status,
                           color=serverColorDict)
    #   returns the template for real time data overview with ^ variables passed to it


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def CPU(slug):  # Slug is the Server Id
    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # sets color of metric
    if tmp.Cpu > 80:
        color = 'danger'
    elif 50 <= tmp.Cpu <= 80:
        color = 'warning'
    elif tmp.Cpu < 50:
        color = 'success'
    else:
        color = 'dark'

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    # gets all cpu usages for this server between dates
    useRange = [metrics.Cpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data
        startdate = sDate.strftime('%Y-%m-%d %H:%M:%S')
        enddate = eDate.strftime('%Y-%m-%d %H:%M:%S')
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
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Cpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Cpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    if avg is not None:
                        dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformats x and adds it to date list
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
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Disk/<slug>', methods=['POST', 'GET'])  # route for Disk usage for a specific server
def disk(slug):  # Slug is the Server Id

    # gets all disk usages for this server between dates
    # diskUse = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '2020-02-29 11:55:00', '2020-02-29 23:55:00'))]

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # sets color of metric
    if tmp.Disk > 90:
        color = 'danger'
    elif 70 <= tmp.Disk <= 90:
        color = 'warning'
    elif tmp.Disk < 70:
        color = 'success'
    else:
        color = 'dark'

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(
        RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
        Metric.Time, maxDateMinus12, maxDate))]

    # gets all Disk usages for this server between dates
    useRange = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
        Metric.Time, maxDateMinus12, maxDate))]

    # partAUse = [metrics.PartA for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '2020-02-29 11:55:00', '2020-02-29 23:55:00'))]
    # partBUse = [metrics.PartB for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '2020-02-29 11:55:00', '2020-02-29 23:55:00'))]
    # partCUse = [metrics.PartC for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '2020-02-29 11:55:00', '2020-02-29 23:55:00'))]
    # partDUse = [metrics.PartD for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
    #     between(Metric.Time, '2020-02-29 11:55:00', '2020-02-29 23:55:00'))]

    parts = []  # list of all partitions for a server

    # Adds unique partition Ids to the list for given server
    for p in Partition.query.filter_by(ServerId=slug).order_by(Partition.PartitionId).filter(between(
            Partition.Time, maxDateMinus12, maxDate)):
        if p.PartitionId not in parts:
            parts.append(p.PartitionId)

    partUse = defaultdict(dict)  # dictionary used for disk table with partitions
    '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and a value of 
    another dictionary. In that dictionary the keys are 'total' which gives you the total disk use for that date and 
    time. The other keys are all of the partition IDs for the server, and the values are that partitions use for that 
    date and time. '''

    # adds disk use from metrics table to dictionary for total
    for row in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
            Metric.Time, maxDateMinus12, maxDate)):
        partUse[row.Time]['total'] = row.Disk

    # Adds a key for each partition with the values of an empty string
    for row in Partition.query.filter_by(ServerId=slug).filter(between(
            Partition.Time, maxDateMinus12, maxDate)):
        for p in parts:
            partUse[row.Time][p] = ''

    # Adds the actual usage for each partition if there is one
    for row in Partition.query.filter_by(ServerId=slug).filter(between(
            Partition.Time, maxDateMinus12, maxDate)):
        for p in parts:
            if p == row.PartitionId:
                partUse[row.Time][p] = row.Usage

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data
        startdate = sDate.strftime('%Y-%m-%d %H:%M:%S')
        enddate = eDate.strftime('%Y-%m-%d %H:%M:%S')
        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
            # Returns list of dates within start and end date
            dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]

            # Returns usages that within  start and end date
            useRange = [metrics.Disk for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                between(Metric.Time, startdate, enddate))]
            # ---------------------------------------------------------------------------------
            # resets parts and partUse to update the date range to the one provided.
            parts = []  # list of all partitions for a server

            # Adds unique partition Ids to the list for given server
            for p in Partition.query.filter_by(ServerId=slug).order_by(Partition.PartitionId).filter(between(
                    Partition.Time, startdate, enddate)):
                if p.PartitionId not in parts:
                    parts.append(p.PartitionId)

            partUse = defaultdict(dict)  # dictionary used for disk table with partitions
            '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and a value of 
            another dictionary. In that dictionary the keys are 'total' which gives you the total disk use for that date and 
            time. The other keys are all of the partition IDs for the server, and the values are that partitions use for that 
            date and time. '''

            # adds disk use from metrics table to dictionary for total
            for row in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
                    Metric.Time, startdate, enddate)):
                partUse[row.Time]['total'] = row.Disk

            # Adds a key for each partition with the values of an empty string
            for row in Partition.query.filter_by(ServerId=slug).filter(between(
                    Partition.Time, startdate, enddate)):
                for p in parts:
                    partUse[row.Time][p] = ''

            # Adds the actual usage for each partition if there is one
            for row in Partition.query.filter_by(ServerId=slug).filter(between(
                    Partition.Time, startdate, enddate)):
                for p in parts:
                    if p == row.PartitionId:
                        partUse[row.Time][p] = row.Usage

        else:  # if difference is grater than 24hrs

            x = sDate  # will be used in iterating the for loop
            y = timedelta(days=1)  # datetime variable that equals 1 day

            while x <= eDate:
                for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                    # x = sDate.date()
                    z = x + y  # z = current value of x plus 1 day

                    # gets the average for each day also temporarily converts x & z to string for query
                    avg = db.session.query(db.func.avg(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Disk).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    if avg is not None:
                        dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformat x and adds it to date list
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
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, partuse=partUse,
                           color=color, partitions=parts)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-GPU/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def gpu(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # sets color of metric
    if tmp.Gpu > 80:
        color = 'danger'
    elif 50 <= tmp.Gpu <= 80:
        color = 'warning'
    elif tmp.Gpu < 50:
        color = 'success'
    else:
        color = 'dark'

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    # gets all Gpu usages for this server between dates
    useRange = [metrics.Gpu for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data
        startdate = sDate.strftime('%Y-%m-%d %H:%M:%S')
        enddate = eDate.strftime('%Y-%m-%d %H:%M:%S')
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
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Gpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Gpu).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    if avg is not None:
                        dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformat x and adds it to date list
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
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-RAM/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ram(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # sets color of metric
    if tmp.Ram > 80:
        color = 'danger'
    elif 50 <= tmp.Ram <= 80:
        color = 'warning'
    elif tmp.Ram < 50:
        color = 'success'
    else:
        color = 'dark'

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    # gets all Ram usages for this server between dates
    useRange = [metrics.Ram for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data
        startdate = sDate.strftime('%Y-%m-%d %H:%M:%S')
        enddate = eDate.strftime('%Y-%m-%d %H:%M:%S')
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
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.Ram).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.Ram).label('average')).order_by(Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    if avg is not None:
                        dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformat x and adds it to date list
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
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Ping/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ping(slug):  # Slug is the Server Id

    form = ChartForm()  # instantiate the chart form class
    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    # sets color and status of metric
    if metric_row.PingLatency != null:
        color = 'success'
        status = "Responding"
    elif metric_row.PingLatency == null:
        color = 'danger'
        status = "Not Responding"
    else:
        color = 'dark'
        status = 'Unknown'

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server between dates
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    # gets all Ping usages for this server between dates
    useRange = [metrics.PingLatency for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    if form.validate_on_submit():  # implementation of user input limiting date range for chart

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)
        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data
        startdate = sDate.strftime('%Y-%m-%d %H:%M:%S')
        enddate = eDate.strftime('%Y-%m-%d %H:%M:%S')
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
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the min for each day also temporarily converts x & z to string for query
                    min = db.session.query(db.func.min(Metric.PingLatency).label('average')).order_by(
                        Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    # gets the max for each day also temporarily converts x & z to string for query
                    max = db.session.query(db.func.max(Metric.PingLatency).label('average')).order_by(
                        Metric.Time).filter_by(
                        ServerId=slug).filter(
                        Metric.Time.between(x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                    if avg is not None:
                        dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformat x and adds it to date list
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
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, status=status, color=color)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
if __name__ == '__main__':  # something for flask
    app.run(debug=True)
