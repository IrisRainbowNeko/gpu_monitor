import sqlite3
import time

from nvitop import Device, GpuProcess, NA

class GPUMonitor:
    def __init__(self, usage_interval=60, details_interval=5):
        # 创建或连接到SQLite数据库
        self.conn = sqlite3.connect('gpu_usage.db')
        self.c = self.conn.cursor()
        self.create_tables()

        self.usage_interval = usage_interval
        self.details_interval = details_interval
        self.details_count = 0

    def create_tables(self):
        # 创建表
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS usage (
                pid INTEGER,
                gpu_id INTEGER,
                user_name TEXT,
                process_name TEXT,
                start_time INTEGER,
                end_time INTEGER,
                min_memory INTEGER,
                max_memory INTEGER,
                sum_memory INTEGER,
                mem_count INTEGER,
                PRIMARY KEY (pid, gpu_id)
            )
        ''')
        self.c.execute('''
            CREATE TABLE IF NOT EXISTS details (
                pid INTEGER,
                gpu_id INTEGER,
                user_name TEXT,
                time_stamp INTEGER,
                memory INTEGER
            )
        ''')
        self.conn.commit()

    def update_usage(self, device, snapshot):
        pid = snapshot.pid
        gpu_memory = (snapshot.gpu_memory // 1024 if snapshot.gpu_memory_human is not NA else 0)

        # 执行SQL查询
        self.c.execute('SELECT * FROM usage WHERE pid = ? AND gpu_id = ?', (pid, device.cuda_index))

        # 获取查询结果
        info = self.c.fetchall()
        if len(info) > 0:
            info = list(info[0])

            self.c.execute(
                "UPDATE usage SET end_time = ?, min_memory = ?, max_memory = ?, sum_memory = ?, mem_count = ? WHERE pid = ? AND gpu_id = ?",
                (int(time.time()),
                 min(info[6], gpu_memory),
                 max(info[7], gpu_memory),
                 info[8] + gpu_memory,
                 info[9] + 1,
                 pid, device.cuda_index))
        else:
            self.c.execute('''INSERT INTO usage (pid, gpu_id, user_name, process_name, start_time, end_time, min_memory, max_memory, sum_memory, mem_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (pid, device.cuda_index, snapshot.username, snapshot.command, int(time.time()), int(time.time()),
                            gpu_memory, gpu_memory, gpu_memory, 1))

    def update_details(self, device, snapshot):
        pid = snapshot.pid
        gpu_memory = (snapshot.gpu_memory // 1024 if snapshot.gpu_memory_human is not NA else 0)

        self.c.execute('''INSERT INTO details (pid, gpu_id, user_name, time_stamp, memory) VALUES (?, ?, ?, ?, ?)''',
                       (pid, device.cuda_index, snapshot.username, int(time.time()), gpu_memory))

    def update(self):
        self.details_count += 1

        devices = Device.cuda.all()  # or `Device.all()` to use NVML ordinal instead
        for device in devices:
            processes = device.processes()
            if len(processes) > 0:
                processes = GpuProcess.take_snapshots(processes.values(), failsafe=True)
                processes.sort(key=lambda process: (process.username, process.pid))

                for snapshot in processes:
                    self.update_usage(device, snapshot)
                    if self.details_count >= self.details_interval:
                        self.update_details(device, snapshot)

        self.conn.commit()

        if self.details_count >= self.details_interval:
            self.details_count = 0

    def start(self):
        try:
            while True:
                self.update()
                time.sleep(self.usage_interval)
        except KeyboardInterrupt:
            pass
        finally:
            self.conn.close()

if __name__ == '__main__':
    # c.execute('SELECT * FROM usage')

    # # 获取查询结果
    # info = c.fetchall()
    # print(info)

    monitor = GPUMonitor(usage_interval=1)
    monitor.start()