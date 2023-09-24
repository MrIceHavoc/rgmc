import os
import math
import torch
import wandb
import tracemalloc

import numpy as np
import matplotlib.pyplot as plt

from matplotlib.ticker import StrMethodFormatter
from torch.utils.data import DataLoader, random_split


def save_epoch_results(m_path, config, device, runtime, batch_number, loss_dict=None):
    print(f'Runtime: {runtime} sec')
    with open(os.path.join(m_path, "results", config['stage'], config['model_out'] + ".txt"), 'a') as file:
        file.write(f'- Runtime: {runtime} sec\n')
    
    if loss_dict is not None:
        with open(os.path.join(m_path, "results", config['stage'], config['model_out'] + ".txt"), 'a') as file:
            for key, value in loss_dict.items():
                value = value / batch_number
                print(f'{key}: {value}')
                file.write(f'- {key}: {value}\n')
                wandb.log({key: value})

    print('Current RAM usage: %f GB'%(tracemalloc.get_traced_memory()[0]/1024/1024/1024))
    print('Peak RAM usage: %f GB'%(tracemalloc.get_traced_memory()[1]/1024/1024/1024))
    if device.type == 'cuda':
        print("Torch CUDA memory allocated: %f GB"%(torch.cuda.memory_allocated(torch.cuda.current_device())/1024/1024/1024))
        print("Torch CUDA memory reserved: %f GB"%(torch.cuda.memory_reserved(torch.cuda.current_device())/1024/1024/1024))
        print("Torch CUDA max memory reserved: %f GB"%(torch.cuda.max_memory_reserved(torch.cuda.current_device())/1024/1024/1024))
    with open(os.path.join(m_path, "results", config['stage'], config['model_out'] + ".txt"), 'a') as file:
        file.write('- Current RAM usage: %f GB\n'%(tracemalloc.get_traced_memory()[0]/1024/1024/1024))
        file.write('- Peak RAM usage: %f GB\n'%(tracemalloc.get_traced_memory()[1]/1024/1024/1024))
        if device.type == 'cuda':
            file.write("- Torch CUDA memory allocated: %f GB\n"%(torch.cuda.memory_allocated(0)/1024/1024/1024))
            file.write("- Torch CUDA memory reserved: %f GB\n"%(torch.cuda.memory_reserved(0)/1024/1024/1024))
            file.write("- Torch CUDA max memory reserved: %f GB\n"%(torch.cuda.max_memory_reserved(0)/1024/1024/1024))

    return

def plot_loss_graph(m_path, config, loss_list_dict, batch_number):
    keys = list(loss_list_dict.keys())
    for idx, key in enumerate(keys):
        loss_values = np.array(loss_list_dict[key])
        epoch_means = np.mean(loss_values.reshape(-1, batch_number), axis=1)
        #epoch_stds = np.std(loss_values.reshape(-1, batch_number), axis=1)
        plt.figure(idx, figsize=(20, 20))
        plt.gca().yaxis.set_major_formatter(StrMethodFormatter('{x:,.10f}'))
        plt.plot(range(len(epoch_means)), epoch_means, label="loss values", color="blue", linewidth=2.0)
        #plt.fill_between(range(len(epoch_stds)), epoch_means-epoch_stds, epoch_means+epoch_stds, color="blue", alpha=0.2)
        plt.axhline(y=epoch_means[-1], color="blue", linestyle="dashed")
        plt.plot(len(epoch_means), epoch_means[-1], marker="o", markersize=5, markeredgecolor="red", markerfacecolor="blue")
        plt.annotate("{:.3f}".format(epoch_means[-1]), xy=(len(epoch_means), epoch_means[-1]), horizontalalignment="left", verticalalignment="bottom")
        plt.xlabel("epoch")
        plt.ylabel(key)
        plt.title(f'{key} per epoch')
        plt.legend()
        plt.savefig(os.path.join(m_path, "results", config['stage'], config['model_out'] + f'_{key}.png'))
        plt.close(idx)

    return

def plot_metrics_bar(m_path, config, losses):
    keys = list(losses.keys())
    X_axis = np.arange(len(keys))
    loss_means = [np.mean(loss) for loss in losses.values()]
    with open(os.path.join(m_path, "results", config["stage"], config["model_out"] + ".txt"), "a") as file:
        for key in keys:
            loss = losses[key][-1]
            print(f'{key}: {loss}')
            file.write(f'- {key}: {loss}\n')
    fig, ax = plt.subplots()
    fig.figsize=(20, 10)
    ax.set_xticks(X_axis)
    ax.set_xticklabels(keys)
    ax.set_title("Loss values of the model")
    ax.yaxis.grid(True)
    metrics_bar = ax.bar(X_axis, loss_means, width=0.4, label="Loss values", align='center', alpha=0.5, ecolor='black', capsize=10)
    ax.bar_label(metrics_bar)
    fig.legend()
    fig.savefig(os.path.join(m_path, "results", config['stage'], config['model_out'] + '_metrics.png'))
    plt.close()
    return

def save_trajectory(path, traj_feats):
    traj_arr = traj_feats.cpu().numpy()
    traj_arr = traj_arr.reshape((traj_arr.size))
    x_arr = traj_arr[0::2]
    y_arr = traj_arr[1::2]
    plt.figure(figsize=(20, 20))
    plt.plot(x_arr, y_arr)
    plt.savefig(os.path.join("checkpoints", "trajectory", path))
    plt.close()     
    return

def save_train_results(m_path, config, train_losses, dataset):
    batch_number = len(iter(DataLoader(dataset, batch_size=config['batch_size'], drop_last=True)))
    plot_loss_graph(m_path, config, train_losses, batch_number)
    plot_metrics_bar(m_path, config, train_losses)
    return

def save_test_results(m_path, config, loss_list_dict):
    plot_metrics_bar(m_path, config, loss_list_dict)
    return

def plot_metric_compare(m_path, config, loss_dict):
    param_values = []
    for model_results in config['model_outs']:
        path = os.path.join(m_path, model_results)
        with open(path, 'r') as res_file:
            for loss_key in loss_dict.keys():
                for line in res_file:
                    if config['param_comp'] in line:
                        param_values.append(np.double(line.removeprefix(f"{config['param_comp']}: ")))
                    if loss_key in line:
                        loss_dict[loss_key].append(np.double(line.removeprefix(f'- {loss_key}: ')))

    X_axis = np.arange(len(config['model_outs']))
    for loss_key in loss_dict.keys():
        fig, ax = plt.subplots()
        fig.figsize=(20, 10)
        ax.set_xticks(X_axis)
        ax.set_xticklabels(param_values)
        title = f"{loss_key} values for different {config['param_comp']} values"
        if config['parent_param'] is not None:
            title = title + f" for {config['parent_param']} hyperparameter"
        ax.set_title(title)
        ax.yaxis.grid(True)
        metric_bar = ax.bar(X_axis, loss_dict[loss_key], width=0.4, align="center", alpha=0.5, ecolor='black', capsize=10)
        ax.bar_label(metric_bar)
        fig.legend()
        out_path = f"{config['architecture']}_{config['dataset']}_{config['param_comp']}.png"
        fig.savefig(os.path.join(m_path, "results", config['stage'], out_path))
        plt.close()
    return
