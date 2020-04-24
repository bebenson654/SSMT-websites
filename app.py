from flask import Flask, render_template, request, redirect, flash, \
    url_for
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField
from wtforms.validators import input_required, Regexp
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import between, null
from sqlalchemy.sql import func
from sqlalchemy.orm.exc import FlushError
from datetime import datetime, timedelta
import pandas as pd
from wtforms.fields.html5 import DateTimeLocalField
from flask_fontawesome import FontAwesome
from _collections import defaultdict

app = Flask(__name__)
app._static_folder = 'static'
app.jinja_env.globals.update(zip=zip)  # allows the use of zip in Jinja
fa = FontAwesome(app)

app.config[
    'SQLALCHEMY_DATABASE_URI'] = 'sqlite:///FinalDatabase1Month.db'  # sets the DB

app.config[
    'SECRET_KEY'] = 's9wSTfZRUfksn5nHu45N'  # secret key used for by WTforms for forms

db = SQLAlchemy(app)
db.Model.metadata.reflect(db.engine)  # Allows SQL alchemy to look into the DB for info on the tables


# -----------------------------------------------------------------------------------------------------------
# Database Tables for SQL alchemy


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
    PartitionId = db.Column(db.Text,
                            primary_key=True)  # primary key column
    Time = db.Column(db.Text, primary_key=True)  # primary key column
    ServerId = db.Column(db.Text,
                         primary_key=True)  # primary key column
    ServerID = db.Column(db.Text, db.ForeignKey('Server.ServerId'))  # foreign key column


# --------------------------------------------------------------------------------------------------------------------
# Global date variables

mDate = Metric.query.order_by(
    Metric.Time.desc()).first()  # gets most recent row from metric
maxDate = mDate.Time  # grabs dateTime as string from row above^

maxDateMinus12 = datetime.strptime(maxDate,
                                   '%Y-%m-%d %H:%M:%S')  # converts it to date time object
maxDateMinus12 = maxDateMinus12 - timedelta(
    hours=12)  # subtracts 12 hrs
maxDateMinus12 = datetime.strftime(maxDateMinus12,
                                   '%Y-%m-%d %H:%M:%S')  # converts back to string

min_Date = Metric.query.order_by(
    Metric.Time).first()  # gets most recent row from metric
minDate = min_Date.Time

maxDateAmerican = datetime.strptime(maxDate,
                                    '%Y-%m-%d %H:%M:%S')  # converts string to DateTime
maxDateAmerican = datetime.strftime(maxDateAmerican,
                                    '%m/%d/%Y %H:%M:%S')  # Converts back to string of max date in American format

minDateAmerican = datetime.strptime(minDate,
                                    '%Y-%m-%d %H:%M:%S')  # converts string to DateTime
minDateAmerican = datetime.strftime(minDateAmerican,
                                    '%m/%d/%Y %H:%M:%S')  # Converts back to string of min date in American format


# ----------------------------------------------------------------------------------------------------------------------
# wtforms forms

class ChartForm(FlaskForm):  # form for the chart date range
    defaultStartDate = datetime.strptime(maxDateMinus12,
                                         '%Y-%m-%d %H:%M:%S')  # default value used for start date field
    defaultEndDate = datetime.strptime(maxDate,
                                       '%Y-%m-%d %H:%M:%S')  # default value used for end date field
    startDate = DateTimeLocalField('StartDate',
                                   default=defaultStartDate,
                                   format='%Y-%m-%dT%H:%M')  # Start date field
    endDate = DateTimeLocalField('EndDate', default=defaultEndDate,
                                 format='%Y-%m-%dT%H:%M')  # End date field


class MasterListForm(FlaskForm):  # form for master list

    # dropdown selector for database type on master list. Requires input
    type = SelectField('type',
                       choices=[(st.TypeId, st.TypeName) for st in
                                ServerType.query.all()],
                       validators=[input_required()])

    # Text field for database ID
    # No spaces, only allows alphanumeric and/or '-' and '_'
    name = StringField('name', validators=[
        input_required(), Regexp('^(\w|-|_)+$',
                                 message='Please only use letters, numbers, "-", or "_", and no spaces')])


class HomeFilter(FlaskForm):  # filter form on home page

    # Dropdown for filtering by database type on home page. Input required
    myChoicesTwo = [('All', 'All')] + [(st.TypeId, st.TypeName) for st
                                       in ServerType.query.all()]
    filter = SelectField('filter', choices=myChoicesTwo,
                         validators=[input_required()])

    # submit field
    sub = SubmitField('Filter')


# ----------------------------------------------------------------------------------------------------------------------
# Function used to color code the servers and their metrics
# returns a dictionary
def getServerAndMetricColor():
    serverColorDict = defaultdict(
        dict)  # initialize the dictionary variable

    servers = Server.query.distinct().all()  # gets all servers

    # sets color for each metric for each server
    for server in servers:
        tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(
            ServerId=server.ServerId).first()
        metric_row = Metric.query.get(
            tmp.MetricId)  # gets the most recent metrics for each server

        if metric_row.Cpu > 80:
            serverColorDict[server.ServerId][
                'CpuColor'] = 'danger'  # sets color to bootstrap red
            serverColorDict[server.ServerId][
                'CpuIcon'] = 'times'  # sets icon to Font Awesome 'x'
        elif 50 <= metric_row.Cpu <= 80:
            serverColorDict[server.ServerId][
                'CpuColor'] = 'warning'  # sets color to bootstrap yellowish
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

        # sets color for each server
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
# Function that provides the date and usage for each metric usage page
def usagePages(metricName, slug):
    # metricName is the name of the column in the Metrics table that you want info from
    # slug is the serverId

    form = ChartForm()  # for = chartForm object

    server = Server.query.filter_by(ServerId=slug).first()  # query for the server specs

    minList = []  # Create empty lists for min, max, and average
    maxList = []
    averageList = []

    tmpLoc = Server.query.filter_by(ServerId=slug).first()
    rack = Rack.query.filter_by(
        RackId=tmpLoc.RackId).first()  # gets rack for this server

    # gets all dates for this server within most recent 12hrs in DB
    dateRange = [metrics.Time for metrics in
                 Metric.query.order_by(Metric.Time).filter_by(
                     ServerId=slug).filter(
                     between(Metric.Time, maxDateMinus12, maxDate))]

    # gets the provided metrics's usages for this server within most recent 12hrs in DB
    useRange = [getattr(metrics, metricName) for metrics in
                Metric.query.order_by(Metric.Time).filter_by(
                    ServerId=slug).filter(
                    between(Metric.Time, maxDateMinus12, maxDate))]

    parts = None  # had to initialize variables for metrics other than disk
    partUse = None

    if metricName == 'Disk':  # gets partitions info if page is Disk

        parts = []  # will be list of all partitions for a server

        # Adds all unique partition Ids to the list for given server
        for p in Partition.query.filter_by(ServerId=slug).order_by(
                Partition.PartitionId).filter(between(
                Partition.Time, maxDateMinus12, maxDate)):
            if p.PartitionId not in parts:
                parts.append(p.PartitionId)

        partUse = defaultdict(
            dict)  # dictionary used for disk table with partitions
        '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and a value 
        of another dictionary. In that dictionary the keys are 'total' which gives you the total disk use for that date 
        and time. The other keys are all of the partition IDs for the server, and the values are that partition's usage for 
        that date and time. '''

        # adds disk use from metrics table to dictionary for total
        for row in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
                Metric.Time, maxDateMinus12, maxDate)):
            partUse[row.Time]['total'] = row.Disk

        # Adds a key for each partition with the values of an empty string
        # this is done so the table will be filled with a empty string if the partition has no usage for that date time
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

        sDate = form.startDate.data  # gets start and end date from form
        eDate = form.endDate.data

        difference = eDate - sDate  # calculating the difference between the start and end date

        startDate = sDate.strftime(
            '%Y-%m-%d %H:%M:%S')  # converts start and end date to string
        endDate = eDate.strftime('%Y-%m-%d %H:%M:%S')

        if sDate < datetime.strptime(minDate,
                                     '%Y-%m-%d %H:%M:%S'):  # warning message is displayed if start date < min
            flash(
                'Warning: There is no data for this metric before ' + minDateAmerican,
                'warning')

        if eDate > datetime.strptime(maxDate,
                                     '%Y-%m-%d %H:%M:%S'):  # warning message is displayed if end date > max
            flash(
                'Warning: There is no data for this metric after ' + maxDateAmerican,
                'warning')

        #
        if difference.total_seconds() < 0:  # error message displayed if the Start date is greater than end date
            flash('Error: Start date is greater than end date', 'danger')

            dateRange = []  # empties list to ensure that no data is given if this error occurs
            useRange = []
        else:
            if difference.total_seconds() <= 86400:  # check to see if the difference is less than 24hrs

                # Returns list of dates within start and end date
                dateRange = [metrics.Time for metrics in
                             Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(
                                 between(Metric.Time, startDate, endDate))]

                # Returns usages for the provided metric that are within start and end date
                useRange = [getattr(metrics, metricName) for metrics in Metric.query.order_by(Metric.Time).filter_by(
                    ServerId=slug).filter(between(Metric.Time, startDate, endDate))]

                # ----------------------------------------------------------------------------------------------------------
                if metricName == 'Disk':
                    # resets parts and partUse to update the date range to the one provided.
                    parts = []  # list of all partitions for a server

                    # Adds unique partition Ids to the list for given server
                    for p in Partition.query.filter_by(
                            ServerId=slug).order_by(
                            Partition.PartitionId).filter(between(
                            Partition.Time, startDate, endDate)):
                        if p.PartitionId not in parts:
                            parts.append(p.PartitionId)

                    partUse = defaultdict(
                        dict)  # dictionary used for disk table with partitions
                    '''PartsUse is a dictionary of dictionaries. The top level dictionary has a key of a Date and Time, and 
                    a value of another dictionary. In that dictionary the keys are 'total' which gives you the total disk 
                    use for that date and time. The other keys are all of the partition IDs for the server, and the values 
                    are that partition's usage for that date and time. '''

                    # adds disk use from metrics table to dictionary for total
                    for row in Metric.query.order_by(Metric.Time).filter_by(ServerId=slug).filter(between(
                            Metric.Time, startDate, endDate)):
                        partUse[row.Time]['total'] = row.Disk

                    # Adds a key for each partition with the values of an empty string
                    # this is done so the table will be filled with a empty string if the partition has no usage for that date time
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
                # x = start date as dateTime object

                y = timedelta(
                    days=1)  # dateTime object that equals 1 day

                while x <= eDate:
                    for p in pd.date_range(sDate,
                                           eDate):  # for loop starting at the start date and ending on end date

                        z = x + y  # z = current value of x plus 1 day

                        # gets the average for each day also temporarily converts x & z to string for query
                        avg = db.session.query(db.func.avg(
                            getattr(Metric, metricName))).order_by(
                            Metric.Time).filter_by(
                            ServerId=slug).filter(Metric.Time.between(
                            x.strftime('%Y-%m-%d'),
                            z.strftime('%Y-%m-%d'))).scalar()

                        # gets the min for each day also temporarily converts x & z to string for query
                        minimum = db.session.query(db.func.min(getattr(Metric, metricName))).order_by(
                            Metric.Time).filter_by(ServerId=slug).filter(Metric.Time.between(
                            x.strftime('%Y-%m-%d'), z.strftime('%Y-%m-%d'))).scalar()

                        # gets the max for each day also temporarily converts x & z to string for query
                        maximum = db.session.query(db.func.max(getattr(Metric, metricName))).order_by(
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

    if not dateRange:  # dateRange is an empty list it gives an error
        flash('There is no data for the given date range', 'info')

    color = getServerAndMetricColor()  # gets server and metric colors using function

    return server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color


# ----------------------------------------------------------------------------------------------------------------------
# Routes for the pages

@app.route('/', methods=['GET',
                         'POST'])  # this is whats at the end of the URL to get to the home page
@app.route('/home', methods=['GET', 'POST'])  # or this
@app.route('/index', methods=['GET', 'POST'])  # or this
def home():
    form = HomeFilter()  # form = WTForms homeFilter object

    server_table = Server.query.all()  # gets entire server table from DB

    serverMetricsDict = {}  # Dictionary used for tooltips on home page

    # Dictionary used for Color coding on home page
    colorDict = getServerAndMetricColor()

    for server in server_table:  # loop to add server id with its metrics to dictionary

        # gets metrics for each server in loop
        metric = Metric.query.order_by(Metric.Time.desc()).filter_by(
            ServerId=server.ServerId).first()

        # sets color based on the color Dictionary
        cpuColor = colorDict[server.ServerId]['CpuColor']
        ramColor = colorDict[server.ServerId]['RamColor']
        gpuColor = colorDict[server.ServerId]['GpuColor']
        diskColor = colorDict[server.ServerId]['DiskColor']
        pingColor = colorDict[server.ServerId]['PingColor']

        # creates key:value for tool tips
        # key is server id, value is string of metrics as seen below
        serverMetricsDict[
            server.ServerId] = f'''<h6 class="text-{cpuColor}"><b>cpu</b>: {str(metric.Cpu)}%</h6>
                                                <h6 class="text-{ramColor}"><b>RAM</b>: {str(metric.Ram)}%</h6>
                                                <h6 class="text-{diskColor}"><b>Disk</b>: {str(metric.Disk)}%</h6>
                                                <h6 class="text-{gpuColor}"><b>GPU</b>: {str(metric.Gpu)}%</h6>
                                                <h6 class="text-{pingColor}"><b>Ping</b>: {str(metric.PingLatency)}ms
                                                </h6>'''

    # filters which servers are shown on home page
    if form.is_submitted():
        if form.filter.data == "All":
            server_table = Server.query.all()  # shows all servers
        else:
            # Only servers with the selected type are shown
            server_table = Server.query.filter_by(
                ServerTypeId=form.filter.data)

    masterList = []  # used to only display servers on the Master List
    for s in MasterList.query.all():
        masterList.append(
            s.Num + '-' + s.Name)  # concatenates strings to make the server id

    # Show only racks that have servers on them
    # rack_table = Rack.query.filter(Rack.RackId == Server.RackId).order_by(Rack.Name)

    # Shows all racks in database
    rack_table = Rack.query.order_by(Rack.Name)

    return render_template('HomePage.html', server=server_table,
                           rack=rack_table, form=form,
                           metric=serverMetricsDict,
                           masterList=masterList,
                           color=colorDict)  # returns home page html doc with these variable


# ----------------------------------------------------------------------------------------------------------------------


@app.route('/masterlist', methods=['GET', 'POST'])  # master list route
def master_list():
    form = MasterListForm()  # form = WTForms MasterList object

    mList = MasterList.query.all()  # gets entire master list table

    if form.validate_on_submit():

        mlType = ServerType.query.get(
            form.type.data)  # gets the row with that type from the server Type table
        try:  # attempt to add the server to the master list table

            # creates a master list object and removes spaces from the name
            ML = MasterList(Type=mlType.TypeName,
                            Name=form.name.data.replace(' ', ''),
                            Num=form.type.data)
            db.session.add(ML)  # adds the object
            db.session.commit()  # commits the change

            # success message if commit was successful
            flash(mlType.TypeName + '-' + form.name.data.replace(' ',
                                                                 '') + ' was added!',
                  'success')

        except FlushError:  # Server Id is not unique

            db.session.rollback()  # rolls back the change

            # displays an error message
            flash(
                'There was an issue adding your server. Make sure the server Id is unique.',
                'danger')

        except:
            db.session.rollback()  # rolls back the change

            # displays an error message
            flash('There was an issue adding your server.', 'danger')

        return redirect(url_for('master_list'))  # reloads the page

    return render_template('MasterList.html', mList=mList,
                           form=form)  # returns the master list page


@app.route("/masterlist/<mlType>&<mlName>/delete", methods=['POST'])  # route used to delete a server from master list
def deleteServer(mlType, mlName):
    # tmp = Master list object to delete
    tmp = MasterList.query.get_or_404((mlType, mlName))

    db.session.delete(tmp)  # deletes tmp
    db.session.commit()  # commits change

    # displays message
    flash(mlType + '-' + mlName + ' has been deleted!', 'info')
    return redirect(
        url_for('master_list'))  # redirects back to master list page


# ----------------------------------------------------------------------------------------------------------------------


@app.route(
    '/data-overview/<slug>')  # route for the  data overview for a specific server
def dataOverview(slug):  # Slug is the Server Id

    server = Server.query.filter_by(
        ServerId=slug).first()  # query for the server specs

    services = Service.query.filter_by(
        ServerId=slug)  # query for the services on this server

    databases = Database.query.filter_by(
        ServerId=slug)  # query for the databases on this server

    runningJobs = RunningJob.query.filter_by(
        ServerId=slug)  # query for the running jobs on this server

    testRJ = RunningJob.query.filter_by(
        ServerId=slug).first()  # hides running job table when empty
    if testRJ is None:
        runningJobs = 0

    testDB = Database.query.filter_by(
        ServerId=slug).first()  # hided DB table when empty
    if testDB is None:
        databases = 0

    rack = Rack.query.filter_by(
        RackId=server.RackId).first()  # gets this server's rack
    location = Location.query.filter_by(
        LocationId=rack.LocationId).first()  # gets that rack's location

    tmp = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerId=slug).first()
    metric_row = Metric.query.get(
        tmp.MetricId)  # gets the most recent metrics for server

    colorDict = getServerAndMetricColor()  # gets colors for metrics

    return render_template('DataOverview.html', server=server,
                           metric=metric_row, service=services,
                           database=databases, runningjob=runningJobs,
                           location=location, rack=rack,
                           color=colorDict)
    #   returns the template for data overview with ^ variables passed to it


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/usage-CPU/<slug>', methods=['POST',
                                         'GET'])  # route for cpu usage for a specific server
def cpu(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerID=slug).first()  # gets this server's most recent metrics

    server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Cpu',
        slug)  # uses the usagePages function to get the data for the chart, table, and color coding

    # return for default date range
    return render_template('Usage-CPU.html', server=server,
                           ametric=metric_row, date=dateRange,
                           usage=useRange,
                           form=form, rack=rack, hi=maxList, lo=minList,
                           avg=averageList, color=color)
    # returns cpu page


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/usage-Disk/<slug>', methods=['POST', 'GET'])  # route for Disk usage for a specific server
def disk(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerID=slug).first()  # gets this server's most recent metrics

    server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Disk',
        slug)  # uses the usagePages function to get the data for the chart, table, and color coding

    return render_template('Usage-Disk.html', server=server,
                           ametric=metric_row, date=dateRange,
                           usage=useRange,
                           form=form, rack=rack, hi=maxList, lo=minList,
                           avg=averageList, partuse=partUse,
                           color=color, partitions=parts)
    # returns disk page


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/usage-GPU/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def gpu(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerID=slug).first()  # gets this server's most recent metrics

    server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Gpu',
        slug)  # uses the usagePages function to get the data for the chart, table, and color coding

    return render_template('Usage-GPU.html', server=server,
                           ametric=metric_row, date=dateRange,
                           usage=useRange,
                           form=form, rack=rack, hi=maxList, lo=minList,
                           avg=averageList, color=color)
    # returns GPU page


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/usage-RAM/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ram(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerID=slug).first()  # gets this server's most recent metrics

    server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color = usagePages(
        'Ram',
        slug)  # uses the usagePages function to get the data for the chart, table, and color coding

    return render_template('Usage-RAM.html', server=server,
                           ametric=metric_row, date=dateRange,
                           usage=useRange,
                           form=form, rack=rack, hi=maxList, lo=minList,
                           avg=averageList, color=color)
    # returns RAM page


# ----------------------------------------------------------------------------------------------------------------------
@app.route('/usage-Ping/<slug>', methods=['POST', 'GET'])  # route for cpu usage for a specific server
def ping(slug):  # Slug is the Server Id

    metric_row = Metric.query.order_by(Metric.Time.desc()).filter_by(
        ServerID=slug).first()  # gets this server's most recent metrics

    server, dateRange, useRange, form, rack, maxList, minList, averageList, partUse, parts, color = usagePages(
        'PingLatency',
        slug)  # uses the usagePages function to get the data for the chart, table, and color coding

    return render_template('Usage-Ping.html', server=server,
                           ametric=metric_row, date=dateRange,
                           usage=useRange,
                           form=form, rack=rack, hi=maxList, lo=minList,
                           avg=averageList, color=color)
    # returns Ping page


# ----------------------------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__':
    app.run()
