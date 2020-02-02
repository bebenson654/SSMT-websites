from flask import Flask, render_template

app = Flask(__name__)

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
    return render_template('HomePage.html')


@app.route('/real-time-data-overview')
def RTDO():
    return render_template('RealTimeDataOverview.html')


@app.route('/usage-cpu')
def usage_CPU():
    return render_template('Usage-CPU.html')


if __name__ == '__main__':
    app.run()
