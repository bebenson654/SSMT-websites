from flask import Flask, render_template, request, redirect, flash, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, Field
from wtforms.validators import input_required, NoneOf, AnyOf, Regexp
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import between, null
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import FlushError
from datetime import date, datetime, timedelta
import pandas as pd
from wtforms.fields.html5 import DateTimeLocalField
from flask_fontawesome import FontAwesome
from _collections import defaultdict

app = Flask(__name__)  # something for flask
app._static_folder = 'static'
app.jinja_env.globals.update(zip=zip)
fa = FontAwesome(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///FinalDatabase1Month.db'  # sets the DB to the stubDB

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
    ServerID = db.Column(db.Text, db.ForeignKey('server.ServerId'))  # foreign key column


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
# Global date variables

mDate = Metric.query.order_by(Metric.Time.desc()).first()  # gets most recent row from metric

maxDate = mDate.Time  # grabs time from row above^

maxDateMinus12 = datetime.strptime(maxDate, '%Y-%m-%d %H:%M:%S')  # converts it to date time object
maxDateMinus12 = maxDateMinus12 - timedelta(hours=12)  # subtracts 12 hrs
maxDateMinus12 = datetime.strftime(maxDateMinus12, '%Y-%m-%d %H:%M:%S')  # converts back to string


# ----------------------------------------------------------------------------------------------------------------------
# wtforms forms

class ChartForm(FlaskForm):  # form for the chart range
    defaultStartDate = datetime.strptime(maxDateMinus12, '%Y-%m-%d %H:%M:%S')
    defaultEndDate = datetime.strptime(maxDate, '%Y-%m-%d %H:%M:%S')
    startdate = DateTimeLocalField('StartDate', default=defaultStartDate, format='%Y-%m-%dT%H:%M')
    enddate = DateTimeLocalField('EndDate', default=defaultEndDate, format='%Y-%m-%dT%H:%M')


class MasterListForm(FlaskForm):  # form for master list
    type = SelectField('type', choices=[(st.TypeId, st.TypeName) for st in ServerType.query.all()],
                       validators=[input_required()])

    # only allows alphanumeric and/or '-' and '_'   No spaces either
    name = StringField('name', validators=[
        input_required(), Regexp('^(\w|-|_)+$', message='Please only use letters, numbers, "-", or "_"')])

    add = SubmitField()


class HomeFilter(FlaskForm):  # filter form on home page
    filter = SelectField('filter', choices=[(st.TypeId, st.TypeName) for st in ServerType.query.all()],
                         validators=[input_required()], )
    sub = SubmitField('Filter')


# ----------------------------------------------------------------------------------------------------------------------
def getServerAndMetricColor():
    serverColorDict = defaultdict(dict)
    servers = Server.query.distinct().all()

    for server in servers:
        tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=server.ServerId).first()
        metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

        if metric_row.Cpu > 80:
            serverColorDict[server.ServerId]['CpuColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId]['CpuIcon'] = 'times'  # sets icon to Font Awesome 'x'
        elif 50 <= metric_row.Cpu <= 80:
            serverColorDict[server.ServerId]['CpuColor'] = 'warning'  # sets color to bootstrap yellowish
            serverColorDict[server.ServerId][
                'CpuIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
        elif metric_row.Cpu < 50:
            serverColorDict[server.ServerId]['CpuColor'] = 'success'  # sets color to bootstrap green
            serverColorDict[server.ServerId]['CpuIcon'] = 'check'  # sets icon to Font Awesome check
        else:
            serverColorDict[server.ServerId]['CpuColor'] = 'dark'  # sets color to bootstrap black
            serverColorDict[server.ServerId]['CpuIcon'] = 'question'  # sets icon to Font Awesome '?'

        if metric_row.Gpu > 80:
            serverColorDict[server.ServerId]['GpuColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId]['GpuIcon'] = 'times'  # sets icon to Font Awesome 'x'
        elif 50 <= metric_row.Gpu <= 80:
            serverColorDict[server.ServerId]['GpuColor'] = 'warning'  # sets color to bootstrap yellowish
            serverColorDict[server.ServerId][
                'GpuIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
        elif metric_row.Gpu < 50:
            serverColorDict[server.ServerId]['GpuColor'] = 'success'  # sets color to bootstrap green
            serverColorDict[server.ServerId]['GpuIcon'] = 'check'  # sets icon to Font Awesome check
        else:
            serverColorDict[server.ServerId]['GpuColor'] = 'dark'  # sets color to bootstrap black
            serverColorDict[server.ServerId]['GpuIcon'] = 'question'  # sets icon to Font Awesome '?'

        if metric_row.Ram > 80:
            serverColorDict[server.ServerId]['RamColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId]['RamIcon'] = 'times'  # sets icon to Font Awesome 'x'
        elif 50 <= metric_row.Ram <= 80:
            serverColorDict[server.ServerId]['RamColor'] = 'warning'  # sets color to bootstrap yellowish
            serverColorDict[server.ServerId][
                'RamIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
        elif metric_row.Ram < 50:
            serverColorDict[server.ServerId]['RamColor'] = 'success'  # sets color to bootstrap green
            serverColorDict[server.ServerId]['RamIcon'] = 'check'  # sets icon to Font Awesome check
        else:
            serverColorDict[server.ServerId]['RamColor'] = 'dark'  # sets color to bootstrap black
            serverColorDict[server.ServerId]['RamIcon'] = 'question'  # sets icon to Font Awesome '?'

        if metric_row.Disk > 90:
            serverColorDict[server.ServerId]['DiskColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId]['DiskIcon'] = 'times'  # sets icon to Font Awesome 'x'
        elif 70 <= metric_row.Disk <= 90:
            serverColorDict[server.ServerId]['DiskColor'] = 'warning'  # sets color to bootstrap yellowish
            serverColorDict[server.ServerId][
                'DiskIcon'] = 'exclamation-triangle'  # sets icon to Font Awesome warning triangle
        elif metric_row.Disk < 70:
            serverColorDict[server.ServerId]['DiskColor'] = 'success'  # sets color to bootstrap green
            serverColorDict[server.ServerId]['DiskIcon'] = 'check'  # sets icon to Font Awesome check
        else:
            serverColorDict[server.ServerId]['Disk'] = 'dark'  # sets color to bootstrap black
            serverColorDict[server.ServerId]['DiskIcon'] = 'question'  # sets icon to Font Awesome '?'

        if metric_row.PingLatency != null:
            serverColorDict[server.ServerId]['PingStatus'] = "Responding"  # sets status of ping
            serverColorDict[server.ServerId]['PingColor'] = 'success'  # sets color to bootstrap green
            serverColorDict[server.ServerId]['PingIcon'] = 'check'  # sets icon to Font Awesome check
        elif metric_row.PingLatency == null:
            serverColorDict[server.ServerId]['PingStatus'] = "Not Responding"  # sets status of ping
            serverColorDict[server.ServerId]['PingColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId]['PingIcon'] = 'times'  # sets icon to Font Awesome 'x'
        else:
            serverColorDict[server.ServerId]['PingStatus'] = "Unknown"  # sets status of ping
            serverColorDict[server.ServerId]['PingColor'] = 'dark'  # sets color to bootstrap black
            serverColorDict[server.ServerId]['PingIcon'] = 'question'  # sets icon to Font Awesome '?'

        #
        if metric_row.Cpu > 80 or metric_row.Disk > 90 or metric_row.Ram > 80 or metric_row.Gpu > 90 or \
                metric_row.PingLatency is None:
            serverColorDict[server.ServerID]['ServerColor'] = 'danger'
            serverColorDict[server.ServerID]['ServerIcon'] = 'times'

        elif 50 <= metric_row.Cpu <= 80 or 70 <= metric_row.Disk <= 90 or 50 <= metric_row.Ram <= 80 or \
                50 <= metric_row.Gpu <= 80:
            serverColorDict[server.ServerID]['ServerColor'] = 'warning'
            serverColorDict[server.ServerID]['ServerIcon'] = 'exclamation-triangle'
        elif metric_row.Cpu < 50 or metric_row.Disk < 70 or metric_row.Ram < 50 or metric_row.Gpu < 50 or \
                metric_row.PingLatency is not None:
            serverColorDict[server.ServerID]['ServerColor'] = 'success'
            serverColorDict[server.ServerID]['ServerIcon'] = 'check'
        else:
            serverColorDict[server.ServerID]['ServerColor'] = 'light'
            serverColorDict[server.ServerID]['ServerIcon'] = 'question'

    return serverColorDict


# ----------------------------------------------------------------------------------------------------------------------
# Function/Method used for usage pages
def usagePages(metricName, slug):
    # metricName is the name of the column in the Metrics table that you ant info from
    # slug is the serverId

    form = ChartForm()  # instantiate the chart form class

    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    minList = []  # Create empty lists for min, max, average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    tmpLoc2 = Rack.query.filter_by(RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server within most recent 12hrs in DB
    dateRange = [metrics.Time for metrics in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
        between(Metric.Time, maxDateMinus12, maxDate))]

    # gets all metric usages for this server within most recent 12hrs in DB
    useRange = [getattr(metrics, metricName) for metrics in Metric.query.order_by(Metric.Time).filter_by(
        ServerId=slug).filter(between(Metric.Time, maxDateMinus12, maxDate))]

    parts = ''  # had to initialize variables for metrics other than disk
    partUse = ''

    if metricName == 'Disk':  # code for getting partitions info if page is Disk

        parts = []  # will be list of all partitions for a server

        # Adds all unique partition Ids to the list for given server
        for p in Partition.query.filter_by(ServerId=slug).order_by(Partition.PartitionId).filter(between(
                Partition.Time, maxDateMinus12, maxDate)):
            if p.PartitionId not in parts:
                parts.append(p.PartitionId)

        partUse = defaultdict(dict)  # dictionary used for disk table with partitions
        '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and a value 
        of another dictionary. In that dictionary the keys are 'total' which gives you the total disk use for that date 
        and time. The other keys are all of the partition IDs for the server, and the values are that partitions use for 
        that date and time. '''

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

    if form.validate_on_submit():  # true if user provides valid date range for chart & table

        dateRange = []  # empties dates to be refilled by code below

        form = ChartForm(request.form)  # gets provided info from form

        sDate = form.startdate.data  # gets start and end date from form
        eDate = form.enddate.data

        startDate = sDate.strftime('%Y-%m-%d %H:%M:%S')  # converts to string
        endDate = eDate.strftime('%Y-%m-%d %H:%M:%S')

        difference = eDate - sDate  # calculating the difference between the start and end date

        if difference.total_seconds() < 0:
            flash('Error: Start date is greater than end date', 'danger')

            dateRange = []
            useRange = []
        else:

            if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs
                # Returns list of dates within start and end date
                dateRange = [metrics.Time for metrics in
                             Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                                 between(Metric.Time, startDate, endDate))]

                # Returns usages that within  start and end date
                useRange = [getattr(metrics, metricName) for metrics in Metric.query.order_by(Metric.Time).filter_by(
                    ServerId=slug).filter(between(Metric.Time, startDate, endDate))]

                # ----------------------------------------------------------------------------------------------------------
                if metricName == 'disk':
                    # resets parts and partUse to update the date range to the one provided.
                    parts = []  # list of all partitions for a server

                    # Adds unique partition Ids to the list for given server
                    for p in Partition.query.filter_by(ServerId=slug).order_by(Partition.PartitionId).filter(between(
                            Partition.Time, startDate, endDate)):
                        if p.PartitionId not in parts:
                            parts.append(p.PartitionId)

                    partUse = defaultdict(dict)  # dictionary used for disk table with partitions
                    '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and 
                    a value of another dictionary. In that dictionary the keys are 'total' which gives you the total disk 
                    use for that date and time. The other keys are all of the partition IDs for the server, and the values 
                    are that partitions use for that date and time. '''

                    # adds disk use from metrics table to dictionary for total
                    for row in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
                            Metric.Time, startDate, endDate)):
                        partUse[row.Time]['total'] = row.Disk

                    # Adds a key for each partition with the values of an empty string
                    for row in Partition.query.filter_by(ServerId=slug).filter(between(
                            Partition.Time, startDate, endDate)):
                        for p in parts:
                            partUse[row.Time][p] = ''

                    # Adds the actual usage for each partition if there is one
                    for row in Partition.query.filter_by(ServerId=slug).filter(between(
                            Partition.Time, startDate, endDate)):
                        for p in parts:
                            if p == row.PartitionId:
                                partUse[row.Time][p] = row.Usage

            else:  # if deference is grater than 24hrs

                x = sDate  # will be used in iterating the for loop
                y = timedelta(days=1)  # datetime variable that equals 1 day

                while x <= eDate:
                    for p in pd.date_range(sDate, eDate):  # for loop starting at the start date and ending on end date
                        # x = sDate.date()
                        z = x + y  # z = current value of x plus 1 day

                        # gets the average for each day also temporarily converts x & z to string for query
                        avg = db.session.query(db.func.avg(getattr(Metric, metricName)).label('average')).order_by(
                            Metric.Time).filter_by(ServerId=slug).filter(Metric.Time.between(
                            x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                        # gets the min for each day also temporarily converts x & z to string for query
                        minimum = db.session.query(db.func.min(getattr(Metric, metricName)).label('average')).order_by(
                            Metric.Time).filter_by(ServerId=slug).filter(Metric.Time.between(
                            x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                        # gets the max for each day also temporarily converts x & z to string for query
                        maximum = db.session.query(db.func.max(getattr(Metric, metricName)).label('average')).order_by(
                            Metric.Time).filter_by(ServerId=slug).filter(Metric.Time.between(
                            x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                        if avg is not None:  # prevents trying to round None and chart from having dates with no data
                            dateRange.append(x.date().strftime('%Y-%m-%d'))  # reformat x and adds it to date list
                            averageList.append(round(avg, 1))  # rounds avg to 1 decimal place and adds it to list
                        minList.append(minimum)  # adds min to list
                        maxList.append(maximum)  # adds MAX to list

                        x = x + y  # adds 1 day to x to iterate through loop

    if len(minList) == 0:  # checks to see if min list is empty | will be empty if date range < 24hrs
        minList = 'xxx'  # sets empty lists to string which will be checked for in the html file
        maxList = 'xxx'
        averageList = 'xxx'

    if not dateRange:
        flash('There is no data for the given date range', 'info')

    color = getServerAndMetricColor()

    return server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color


# ----------------------------------------------------------------------------------------------------------------------
# Routes for the pages

@app.route('/', methods=['GET', 'POST'])  # this is whats at the end of the URL to get to the home page
@app.route('/home', methods=['GET', 'POST'])  # or this
def home():
    form = HomeFilter()
    server_table = Server.query.all()

    serverMetricsDict = {}  # Dictionary used for tooltips on home page

    # Dictionary used for Color coding on home page
    colorDict = getServerAndMetricColor()

    for server in server_table:  # loop to add server id with its metrics to dictionary

        # gets metrics for each server in loop
        metric = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerId=server.ServerId).first()

        cpuColor = colorDict[server.ServerId]['CpuColor']
        ramColor = colorDict[server.ServerId]['RamColor']
        gpuColor = colorDict[server.ServerId]['GpuColor']
        diskColor = colorDict[server.ServerId]['DiskColor']
        pingColor = colorDict[server.ServerId]['PingColor']

        # creates key:value for tool tips
        # key is server id, value is string of metrics as seen below
        serverMetricsDict[server.ServerId] = f'''<h6 class="text-{cpuColor}"><b>CPU</b>: {str(metric.Cpu)}%</h6>
                                                <h6 class="text-{ramColor}"><b>RAM</b>: {str(metric.Ram)}%</h6>
                                                <h6 class="text-{diskColor}"><b>Disk</b>: {str(metric.Disk)}%</h6>
                                                <h6 class="text-{gpuColor}"><b>GPU</b>: {str(metric.Gpu)}%</h6>
                                                <h6 class="text-{pingColor}"><b>Ping</b>: {str(metric.PingLatency)}ms
                                                </h6>'''

    if form.validate_on_submit():
        server_table = Server.query.filter_by(
            ServerTypeId=form.filter.data)  # query that gets all of the servers in the Server table

    masterList = []  # used to only display servers on the Master List
    for s in MasterList.query.all():
        masterList.append(s.Num + '-' + s.Name)  # concatenates strings to make the server id

    #  rack_table = Rack.query.filter(Rack.RackId == Server.RackId).order_by(Rack.Name)  # Show only racks that have
    #                                                                                       servers on them
    rack_table = Rack.query.order_by(Rack.Name)  # Shows all racks in database

    return render_template('HomePageV2.html', server=server_table, rack=rack_table, form=form, metric=serverMetricsDict,
                           masterList=masterList, color=colorDict)  # returns V2 home page html doc with that variable


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/masterlist', methods=['GET', 'POST'])  # master list route
def master_list():
    form = MasterListForm()

    mList = MasterList.query.all()

    if form.validate_on_submit():
        mlType = ServerType.query.get(form.type.data)

        try:
            # spaces are removed from the name
            ML = MasterList(Type=mlType.TypeName, Name=form.name.data.replace(' ', ''), Num=form.type.data)
            db.session.add(ML)
            db.session.commit()
            flash(mlType.TypeName + '-' + form.name.data.replace(' ', '') + ' was added!', 'success')
        except FlushError:
            db.session.rollback()
            flash('There was an issue adding your server. Make sure the server Id is unique.', 'danger')
        return redirect(url_for('master_list'))
    return render_template('MasterList.html', mList=mList, form=form)  # only returns the hard-coded master list for now


@app.route("/masterlist/<mlType>&<mlName>/delete", methods=['POST'])  # route used to delete a server from master list
def deleteServer(mlType, mlName):
    tmp = MasterList.query.get_or_404((mlType, mlName))

    db.session.delete(tmp)
    db.session.commit()
    flash(mlType + '-' + mlName + ' has been deleted!', 'info')
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

    colorDict = getServerAndMetricColor()

    return render_template('RealTimeDataOverviewTemp.html', server=server, metric=metric_row, service=services,
                           database=databases, runningjob=runningjobs, location=tmpLoc3, rack=tmpLoc2,
                           color=colorDict)
    #   returns the template for real time data overview with ^ variables passed to it


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-cpu/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def CPU(slug):  # Slug is the Server Id

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()

    server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Cpu', slug)

    # return for default date range
    return render_template('Usage-CPUTemp.html', server=server, ametric=tmp, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Disk/<slug>', methods=['POST', 'GET'])  # route for Disk usage for a specific server
def disk(slug):  # Slug is the Server Id

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Disk', slug)

    return render_template('Usage-Disk.html', server=server, ametric=tmp, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, partuse=partUse,
                           color=color, partitions=parts)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-GPU/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def gpu(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()

    server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Gpu', slug)

    return render_template('Usage-GPU.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-RAM/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ram(slug):  # Slug is the Server Id

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Ram', slug)

    return render_template('Usage-RAM.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/usage-Ping/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ping(slug):  # Slug is the Server Id

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(ServerID=slug).first()
    metric_row = Metric.query.get(tmp.MetricId)  # gets the most recent metrics for server

    server, dateRange, useRange, form, tmpLoc2, maxList, minList, averageList, partUse, parts, color = usagePages(
        'PingLatency', slug)

    return render_template('Usage-Ping.html', server=server, ametric=metric_row, date=dateRange, usage=useRange,
                           form=form, rack=tmpLoc2, hi=maxList, lo=minList, avg=averageList, color=color)


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':  # something for flask
    app.run()
