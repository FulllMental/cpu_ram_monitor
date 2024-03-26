import base64
from io import BytesIO

import matplotlib.pyplot as plt
import paramiko
from environs import Env
from flask import Flask, render_template

app = Flask(__name__)
historical_data = {}


def get_server_data(ip, username, password):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=username, password=password)
    stdin_cpu, stdout_cpu, stderr_cpu = ssh.exec_command('top -bn1 | grep "Cpu(s)"')
    stdin_ram, stdout_ram, stderr_ram = ssh.exec_command('free | grep Mem')

    cpu_usage = float(stdout_cpu.read().decode().strip().split()[1].replace('%us,', ''))
    ram_info = stdout_ram.read().decode().split()
    total_ram = int(ram_info[1])
    used_ram = int(ram_info[2])
    ram_usage = (used_ram / total_ram) * 100

    ssh.close()

    return cpu_usage, ram_usage


def clear_data(data_to_clear):
    if len(data_to_clear) > 12:
        data_to_clear.pop(0)


@app.route('/')
def index():
    for server, data in historical_data.items():
        cpu_usage, ram_usage = get_server_data(data['ip'], data['username'], data['password'])
        data['cpu_data'].append(cpu_usage)
        data['ram_data'].append(ram_usage)
        clear_data(data['cpu_data'])
        clear_data(data['ram_data'])

    plt.figure(figsize=(12, 10))

    idx = 1
    for server, data in historical_data.items():
        plt.subplot(len(historical_data), 1, idx)
        plt.plot(data['cpu_data'], color='blue', label='CPU Usage')
        plt.plot(data['ram_data'], color='green', label='RAM Usage')
        plt.title(f'Server: {data["ip"]} Usage Over Time')
        plt.xlabel('Time')
        plt.ylabel('Usage (%)')
        plt.legend()
        idx += 1

    img = BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)

    img_base64 = base64.b64encode(img.getvalue()).decode('utf-8')
    return render_template('index.html', img_base64=img_base64)


if __name__ == '__main__':
    env = Env()
    env.read_env()
    username = env("LOGIN")
    password = env("PASSWORD")
    servers = env.list("SERVERS")
    for indx, server in enumerate(servers):
        historical_data[f'server{indx + 1}'] = {
            'ip': server,
            'username': username,
            'password': password,
            'cpu_data': [],
            'ram_data': []
        }

    app.run(debug=True)
