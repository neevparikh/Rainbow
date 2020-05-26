import argparse
import glob
import os
import sys
import json

import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

sns.set(style="darkgrid")

default_lr = 0.0001

def parse_filepath(fp, bin_size):
    try:
        loss = pd.read_csv(f"{fp}/loss.csv")
        ignore_trailing_n = int(len(loss) - np.floor(len(loss)/bin_size)*bin_size)
        max_idx = len(loss) - ignore_trailing_n
        loss = pd.DataFrame(
                np.einsum(
                    'ijk->ik',
                    loss.values[:max_idx].reshape(-1, bin_size, loss[:max_idx].shape[1])
                    )/bin_size,
                columns=loss.columns)
        with open(f"{fp}/params.json", "r") as json_file:
            params = json.load(json_file)
        for k,v in params.items():
            loss[k] = v
        return loss
    except FileNotFoundError as e:
        print(f"Error in parsing filepath {fp}: {e}")
        return None


def collate_results(results_dir, bin_size):
    dfs = []
    for run in glob.glob(results_dir + '/*'):
        print(f"Found {run}")
        run_df = parse_filepath(run, bin_size)
        if run_df is None:
            continue
        dfs.append(run_df)
    return pd.concat(dfs, axis=0)


def plot(data, hue, style, seed, bin_size, savepath=None, show=True):
    print(f"Plotting using hue={hue}, style={style}, {seed}")

    # If asking for multiple envs, use facetgrid and adjust height
    height = 3 if len(data['env'].unique()) > 2 else 5
    col_wrap = 2 if len(data['env'].unique()) > 1 else 1

    if isinstance(seed, list) or seed == 'average':
        g = sns.relplot(x='step',
                        y='loss',
                        data=data,
                        hue=hue,
                        style=style,
                        kind='line',
                        legend='full',
                        height=height,
                        aspect=1.5,
                        col='env',
                        col_wrap=col_wrap,
                        facet_kws={'sharey': False})

    elif seed == 'all':
        g = sns.relplot(x='step',
                        y='loss',
                        data=data,
                        hue=hue,
                        units='seed',
                        style=style,
                        estimator=None,
                        kind='line',
                        legend='full',
                        height=height,
                        aspect=1.5,
                        col='env',
                        col_wrap=col_wrap,
                        facet_kws={'sharey': False})
    else:
        raise ValueError(f"{seed} not a recognized choice")

    for ax in g.axes.flatten():
        ax.set_xlabel(f"step in {str(bin_size)}s")
        ax.set(ylim=(0, 3)) # TODO make this something like 80% of the points are visible

    if savepath is not None:
        g.savefig(savepath)

    if show:
        plt.show()


def parse_args():
    # Parse input arguments
    # Use --help to see a pretty description of the arguments
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    # yapf: disable
    parser.add_argument('--results-dir', help='Directory for results', default='results/pretraining',
            required=False, type=str)
    parser.add_argument('--create-csv', help='Create csv, overwrites if exists',
            action='store_true')
    parser.add_argument('--bin-size', help='How much to reduce the data by', type=int, default=100)

    parser.add_argument('--query', help='DF query string', type=str)
    parser.add_argument('--hue', help='Hue variable', type=str, )
    parser.add_argument('--style', help='Style variable', type=str)
    parser.add_argument('--seed', help='How to handle seeds', type=str, default='average')

    parser.add_argument('--no-plot', help='No plots', action='store_true')
    parser.add_argument('--no-show', help='Does not show plots', action='store_true')
    parser.add_argument('--save-path', help='Save the plot here', type=str)
    # yapf: enable

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.create_csv:
        print("Recreating csv in results directory")
        print(f"Binning by {args.bin_size}")
        df = collate_results(args.results_dir, args.bin_size)
        df.to_csv(os.path.join(args.results_dir, 'combined.csv'))

    if not args.no_plot:
        if args.save_path:
            os.makedirs(os.path.split(args.save_path)[0], exist_ok=True)
        df = pd.read_csv(os.path.join(args.results_dir, 'combined.csv'))

        if args.query is not None:
            print(f"Filtering with {args.query}")
            df = df.query(args.query)
        plot(df, args.hue, args.style, args.seed, args.bin_size, savepath=args.save_path, show=(not args.no_show))
