import argparse
import json
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
'''
usage : python3 xmTool/loss_plot.py plot_curve work_dirs/cascade_res50_fpn/20200527_230629.log.json --keys loss mAP --legend loss mAP --out loss.png

'''

def cal_train_time(log_dicts, args):
    for i, log_dict in enumerate(log_dicts):
        print(f'{"-" * 5}Analyze train time of {args.json_logs[i]}{"-" * 5}')
        all_times = []
        for epoch in log_dict.keys():
            if args.include_outliers:
                all_times.append(log_dict[epoch]['time'])
            else:
                all_times.append(log_dict[epoch]['time'][1:])
        all_times = np.array(all_times)
        epoch_ave_time = all_times.mean(-1)
        slowest_epoch = epoch_ave_time.argmax()
        fastest_epoch = epoch_ave_time.argmin()
        std_over_epoch = epoch_ave_time.std()
        print(f'slowest epoch {slowest_epoch + 1}, '
              f'average time is {epoch_ave_time[slowest_epoch]:.4f}')
        print(f'fastest epoch {fastest_epoch + 1}, '
              f'average time is {epoch_ave_time[fastest_epoch]:.4f}')
        print(f'time std over epochs is {std_over_epoch:.4f}')
        print(f'average iter time: {np.mean(all_times):.4f} s/iter')
        print()


def plot_curve(log_dicts, args):
    if args.backend is not None:
        plt.switch_backend(args.backend)
    fig, ax1 = plt.subplots()
    # sns.set_style(args.style)
    # if legend is None, use {filename}_{key} as legend
    legend = args.legend
    if legend is None:
        legend = []
        for json_log in args.json_logs:
            for metric in args.keys:
                legend.append(f'{json_log}_{metric}')
    assert len(legend) == (len(args.json_logs) * len(args.keys))
    metrics = args.keys

    num_metrics = len(metrics)
    for i, log_dict in enumerate(log_dicts):
        epochs = list(log_dict.keys())
        for j, metric in enumerate(metrics):
            print(f'plot curve of {args.json_logs[i]}, metric is {metric}')
            if metric not in log_dict[epochs[0]]:
                raise KeyError(
                    f'{args.json_logs[i]} does not contain metric {metric}')

            if 'mAP' in metric:
                xs = np.arange(1, max(epochs) + 1)
                ys = []
                for epoch in epochs:
                    ys += log_dict[epoch][metric]
                ax = plt.gca()
                ax2 = ax.twinx()
                ax2.tick_params(axis='y', labelcolor='tab:blue', labelsize=14)
                ax2.set_ylabel('eval mAP', rotation=-90, fontsize=16)
                ax2.yaxis.set_label_coords(1.15, 0.55)
                ax2.set_ylim([0,1])
                plt.plot(xs, ys, label=legend[i * num_metrics + j], linewidth=1, marker='*')
                # --------------------------------------
            elif 'loss' in metric:
                xs = np.arange(1, max(epochs) + 1)
                ys = []
                for epoch in epochs:
                    loss_ep = np.array(log_dict[epoch][metric])
                    avg_loss = np.mean(loss_ep)
                    ys.append(avg_loss)
                ax = plt.gca()
                plt.xlabel('epoch', fontsize=14)
                ax.set_xticks(xs)
                ax.tick_params(axis='x', labelsize=14)
                ax.tick_params(axis='y', labelcolor='tab:orange', labelsize=14)
                ax.set_ylabel('training loss', fontsize=16)
                ax.set_ylim([0,1.2])
                plt.plot(xs, ys, label=legend[i * num_metrics + j], linewidth=1, marker='x', color='orange')
                # ---------------------------------------
            else:
                xs = []
                ys = []
                num_iters_per_epoch = log_dict[epochs[0]]['iter'][-1]
                for epoch in epochs:
                    iters = log_dict[epoch]['iter']
                    if log_dict[epoch]['mode'][-1] == 'val':
                        iters = iters[:-1]
                    xs.append(
                        np.array(iters) + (epoch - 1) * num_iters_per_epoch)
                    ys.append(np.array(log_dict[epoch][metric][:len(iters)]))
                xs = np.concatenate(xs)
                ys = np.concatenate(ys)
                plt.xlabel('iter')
                plt.plot(
                    xs, ys, label=legend[i * num_metrics + j], linewidth=1)
            # plt.legend()
            plt.tight_layout()
        if args.title is not None:
            plt.title('tra')
    if args.out is None:
        plt.show()
    else:
        print(f'save curve to: {args.out}')
        plt.savefig(args.out)
        plt.cla()


def add_plot_parser(subparsers):
    parser_plt = subparsers.add_parser(
        'plot_curve', help='parser for plotting curves')
    parser_plt.add_argument(
        'json_logs',
        type=str,
        nargs='+',
        help='path of train log in json format')
    parser_plt.add_argument(
        '--keys',
        type=str,
        nargs='+',
        default=['bbox_mAP'],
        help='the metric that you want to plot')
    parser_plt.add_argument('--title', type=str, help='title of figure')
    parser_plt.add_argument(
        '--legend',
        type=str,
        nargs='+',
        default=None,
        help='legend of each plot')
    parser_plt.add_argument(
        '--backend', type=str, default=None, help='backend of plt')
    parser_plt.add_argument(
        '--style', type=str, default='dark', help='style of plt')
    parser_plt.add_argument('--out', type=str, default=None)


def add_time_parser(subparsers):
    parser_time = subparsers.add_parser(
        'cal_train_time',
        help='parser for computing the average time per training iteration')
    parser_time.add_argument(
        'json_logs',
        type=str,
        nargs='+',
        help='path of train log in json format')
    parser_time.add_argument(
        '--include-outliers',
        action='store_true',
        help='include the first value of every epoch when computing '
        'the average time')


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze Json Log')
    # currently only support plot curve and calculate average train time
    subparsers = parser.add_subparsers(dest='task', help='task parser')
    add_plot_parser(subparsers)
    add_time_parser(subparsers)
    args = parser.parse_args()
    return args


def load_json_logs(json_logs):
    # load and convert json_logs to log_dict, key is epoch, value is a sub dict
    # keys of sub dict is different metrics, e.g. memory, bbox_mAP
    # value of sub dict is a list of corresponding values of all iterations
    log_dicts = [dict() for _ in json_logs]
    for json_log, log_dict in zip(json_logs, log_dicts):
        with open(json_log, 'r') as log_file:
            for line in log_file:
                log = json.loads(line.strip())
                # skip lines without `epoch` field
                if 'epoch' not in log:
                    continue
                epoch = log.pop('epoch')
                if epoch not in log_dict:
                    log_dict[epoch] = defaultdict(list)
                for k, v in log.items():
                    log_dict[epoch][k].append(v)
    return log_dicts


def main():
    args = parse_args()

    json_logs = args.json_logs
    for json_log in json_logs:
        assert json_log.endswith('.json')

    log_dicts = load_json_logs(json_logs)

    print(log_dicts[0][1])

    eval(args.task)(log_dicts, args)


if __name__ == '__main__':
    main()
