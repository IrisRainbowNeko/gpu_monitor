import sqlite3

import datetime
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from matplotlib.colors import LinearSegmentedColormap

matplotlib.use('Agg')

def gradientbars(bars, ax, colors):
    #colors = [(1, 0, 0), (0, 0, 1), ]  # first color is red, last is blue
    cm = LinearSegmentedColormap.from_list(
        "Custom", colors, N=256)  # Conver to color map
    mat = np.indices((10, 10))[1]  # define a matrix for imshow
    lim = ax.get_xlim() + ax.get_ylim()
    for bar in bars:
        bar.set_zorder(1)
        bar.set_facecolor("none")

        # get the coordinates of the rectangle
        x_all = bar.get_paths()[0].vertices[:, 0]
        y_all = bar.get_paths()[0].vertices[:, 1]

        # Get the first coordinate (lower left corner)
        x, y = x_all[0], y_all[0]
        # Get the height and width of the rectangle
        h, w = max(y_all) - min(y_all), max(x_all) - min(x_all)
        # Show the colormap
        ax.imshow(mat, extent=[x, x + w, y, y + h], aspect="auto", zorder=0, cmap=cm, alpha=0.2)
    ax.axis(lim)

def plot_bars(occupy, memory=None, N_row=8, colors = ("#FF0000", "#0000FF")):
    fig, axs = plt.subplots(len(occupy), 1, figsize=(12, 10), sharex=True, facecolor="#FFFFFF")
    cmap = plt.cm.RdBu
    dlen = 0.8/N_row

    for i, (name, time_dict) in enumerate(occupy.items()):
        bars = []
        y_datas = [(k+0.5)*dlen-0.5+0.1 for k in range(N_row)]
        for k, time_range in time_dict.items():
            y = (k+0.5)*dlen-0.5+0.1
            for item in time_range:
                date_0 = mdates.date2num(datetime.datetime.fromtimestamp(item[0]))
                date_1 = mdates.date2num(datetime.datetime.fromtimestamp(item[1]))
                #bar = ax.broken_barh([[item[0], item[1]-item[0]]], (i + y-dlen/2, dlen), facecolors=cmap(0.7), alpha=0.0)
                bar = axs[i].broken_barh([[date_0, date_1-date_0]], (0 + y-dlen/2, dlen), facecolors=cmap(0.7), alpha=0.1)
                bars.append(bar)

            if memory is not None:
                t_mem = list(zip(*memory[name][k]))
                date = [mdates.date2num(datetime.datetime.fromtimestamp(t)) for t in t_mem[0]]
                axs[i].plot(date, np.array(t_mem[1])*dlen+y-0.5*dlen, color='green', linewidth=0.5)

        gradientbars(bars, axs[i], colors=colors)
        axs[i].grid(which='major', axis='x', linestyle='-', alpha=0.4, color="#C8C9C9")
        axs[i].set_ylim(-0.5, 0.5)
        #axs[i].set_yticks(y_datas, [str(r) for r in range(N_row)])
        axs[i].set_yticks(y_datas)
        axs[i].set_yticklabels([str(r) for r in range(N_row)])
        axs[i].set_ylabel(name)

    axs[-1].tick_params(axis="x", which="major", length=0, labelsize=14, colors='#C8C9C9')

    axs[-1].xaxis.set_major_formatter(mdates.DateFormatter('%m-%d-%H:%M'))
    fig.autofmt_xdate()

    axs[-1].set_axisbelow(True)
    #plt.setp(axs[:-1], xticks=[])

    fig.tight_layout()

    #plt.show()

class InfoViser:
    def __init__(self, db='gpu_usage.db') -> None:
        self.conn = sqlite3.connect(db)
        self.c = self.conn.cursor()

    def load_usage(self):
        self.c.execute('SELECT * FROM usage')
        info = self.c.fetchall()
        data = {}
        for item in info:
            gpu_id = item[1]
            user_name = item[2]
            start_time = item[4]
            end_time = item[5]
            # avg_mem = item[8]/item[9]

            if user_name not in data:
                data[user_name] = {}
            if gpu_id not in data[user_name]:
                data[user_name][gpu_id] = []

            data[user_name][gpu_id].append((start_time, end_time))
        return data

    def load_detail(self, max_memory=24*1024*1024):
        '''
        {
            user_name:{
                gpu_id: {time_stamp1: memory1, time_stamp2: memory2}
            }
        }

        '''
        self.c.execute('SELECT * FROM details')
        info = self.c.fetchall()
        data = {}
        for item in info:
            gpu_id = item[1]
            user_name = item[2]
            time_stamp = item[3]
            memory = item[4]

            if user_name not in data:
                data[user_name] = {}
            if gpu_id not in data[user_name]:
                data[user_name][gpu_id] = {}

            if time_stamp not in data[user_name][gpu_id]:
                data[user_name][gpu_id][time_stamp] = memory
            else:
                data[user_name][gpu_id][time_stamp] += memory

        # 对time_stamp排序
        for user_name, user_data in data.items():
            for gpu_id, gpu_data in user_data.items():
                gpu_data = {k: v/max_memory for k, v in gpu_data.items()}
                gpu_data = sorted(gpu_data.items(), key=lambda item: item[0])
                user_data[gpu_id] = gpu_data

        return data

    def vis_usage_memory(self, out_path='gpu_usage.png'):
        usage_data = self.load_usage()
        memory_data = self.load_detail()

        plot_bars(usage_data, memory_data)

        plt.savefig(out_path)
        plt.close()


if __name__ == '__main__':

    viser = InfoViser()
    viser.vis_usage_memory()