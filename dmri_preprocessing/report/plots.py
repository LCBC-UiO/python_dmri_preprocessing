#!/bin/env python
import nibabel as nb
import numpy as np
import pandas as pd
from nilearn.image import threshold_img, load_img
from niworkflows.viz.utils import cuts_from_bbox, compose_view, plot_registration
from niworkflows.viz.plots import plot_carpet

import matplotlib.pyplot as plt
from matplotlib import gridspec as mgs
from matplotlib import animation

import seaborn as sns
from seaborn import color_palette

def plot_before_after_svg(path_to_nii_before,path_to_nii_after,path_to_mask_nii,path_to_output_svg):
    """
    Outputs a switching svg file to be included in qc reports.

    Uses the niworkflows package to do this.
    """
    before_nii = load_img(path_to_nii_before)
    after_nii = load_img(path_to_nii_after)
    mask_nii = load_img(path_to_mask_nii)

    cuts = cuts_from_bbox(mask_nii, cuts=7)
    before_plot = plot_registration(before_nii,'before',cuts=cuts,label="before",estimate_brightness=True)
    after_plot = plot_registration(after_nii,'after',cuts=cuts,label="after",estimate_brightness=True)
    compose_view(before_plot,after_plot,out_file=path_to_output_svg)

# Taken from: https://github.com/PennBBL/qsiprep/blob/master/qsiprep/interfaces/niworkflows.py
def plot_sliceqc(slice_data, nperslice, size=(950, 800),
                 subplot=None, title=None, output_file=None,
                 lut=None, tr=None):
    """
    Plot an image representation of voxel intensities across time also know
    as the "carpet plot" or "Power plot". See Jonathan Power Neuroimage
    2017 Jul 1; 154:150-158.
    Parameters
    ----------
        slice_data: 2d array
            errors in each slice for each volume
        nperslice: 1d array
            number of voxels included in each slice
        axes : matplotlib axes, optional
            The axes used to display the plot. If None, the complete
            figure is used.
        title : string, optional
            The title displayed on the figure.
        output_file : string, or None, optional
            The name of an image file to export the plot to. Valid extensions
            are .png, .pdf, .svg. If output_file is not None, the plot
            is saved to a file, and the display is closed.
        tr : float , optional
            Specify the TR, if specified it uses this value. If left as None,
            # Frames is plotted instead of time.
    """

    # Define TR and number of frames
    notr = False
    if tr is None:
        notr = True
        tr = 1.

    # If subplot is not defined
    if subplot is None:
        subplot = mgs.GridSpec(1, 1)[0]

    # Define nested GridSpec
    wratios = [1, 100]
    gs = mgs.GridSpecFromSubplotSpec(1, 2, subplot_spec=subplot,
                                     width_ratios=wratios,
                                     wspace=0.0)

    # Segmentation colorbar
    ax0 = plt.subplot(gs[0])
    ax0.set_yticks([])
    ax0.set_xticks([])
    ax0.imshow(nperslice[:, np.newaxis], interpolation='nearest', aspect='auto', cmap='plasma')
    ax0.grid(False)
    ax0.spines["left"].set_visible(False)
    ax0.spines["bottom"].set_color('none')
    ax0.spines["bottom"].set_visible(False)

    # Carpet plot
    ax1 = plt.subplot(gs[1])
    ax1.imshow(slice_data, interpolation='nearest', aspect='auto', cmap='viridis')
    ax1.grid(False)
    ax1.set_yticks([])
    ax1.set_yticklabels([])

    # Set 10 frame markers in X axis
    interval = max((int(slice_data.shape[1] + 1) // 10, int(slice_data.shape[1] + 1) // 5, 1))
    xticks = list(range(0, slice_data.shape[1])[::interval])
    ax1.set_xticks(xticks)
    if notr:
        ax1.set_xlabel('time (frame #)')
    else:
        ax1.set_xlabel('time (s)')
    labels = tr * (np.array(xticks))
    ax1.set_xticklabels(['%.02f' % t for t in labels.tolist()], fontsize=5)

    # Remove and redefine spines
    for side in ["top", "right"]:
        # Toggle the spine objects
        ax0.spines[side].set_color('none')
        ax0.spines[side].set_visible(False)
        ax1.spines[side].set_color('none')
        ax1.spines[side].set_visible(False)

    ax1.yaxis.set_ticks_position('left')
    ax1.xaxis.set_ticks_position('bottom')
    ax1.spines["bottom"].set_visible(False)
    ax1.spines["left"].set_color('none')
    ax1.spines["left"].set_visible(False)

    if output_file is not None:
        figure = plt.gcf()
        figure.savefig(output_file, bbox_inches='tight')
        plt.close(figure)
        figure = None
        return output_file

    return [ax0, ax1], gs

# Taken from: https://github.com/PennBBL/qsiprep/blob/master/qsiprep/interfaces/niworkflows.py
def confoundplot(tseries, gs_ts, gs_dist=None, name=None,
                 units=None, tr=None, hide_x=True, color='b', nskip=0,
                 cutoff=None, ylims=None):

    # Define TR and number of frames
    notr = False
    if tr is None:
        notr = True
        tr = 1.
    ntsteps = len(tseries)
    tseries = np.array(tseries)

    # Define nested GridSpec
    gs = mgs.GridSpecFromSubplotSpec(1, 2, subplot_spec=gs_ts,
                                     width_ratios=[1, 100], wspace=0.0)

    ax_ts = plt.subplot(gs[1])
    ax_ts.grid(False)

    # Set 10 frame markers in X axis
    interval = max((ntsteps // 10, ntsteps // 5, 1))
    xticks = list(range(0, ntsteps)[::interval])
    ax_ts.set_xticks(xticks)

    if not hide_x:
        if notr:
            ax_ts.set_xlabel('time (frame #)')
        else:
            ax_ts.set_xlabel('time (s)')
            labels = tr * np.array(xticks)
            ax_ts.set_xticklabels(['%.02f' % t for t in labels.tolist()])
    else:
        ax_ts.set_xticklabels([])

    if name is not None:
        if units is not None:
            name += ' [%s]' % units

        ax_ts.annotate(
            name, xy=(0.0, 0.7), xytext=(0, 0), xycoords='axes fraction',
            textcoords='offset points', va='center', ha='left',
            color=color, size=8,
            bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'none',
                  'color': 'none', 'lw': 0, 'alpha': 0.8})

    for side in ["top", "right"]:
        ax_ts.spines[side].set_color('none')
        ax_ts.spines[side].set_visible(False)

    if not hide_x:
        ax_ts.spines["bottom"].set_position(('outward', 20))
        ax_ts.xaxis.set_ticks_position('bottom')
    else:
        ax_ts.spines["bottom"].set_color('none')
        ax_ts.spines["bottom"].set_visible(False)

    # ax_ts.spines["left"].set_position(('outward', 30))
    ax_ts.spines["left"].set_color('none')
    ax_ts.spines["left"].set_visible(False)
    # ax_ts.yaxis.set_ticks_position('left')

    ax_ts.set_yticks([])
    ax_ts.set_yticklabels([])

    nonnan = tseries[~np.isnan(tseries)]
    if nonnan.size > 0:
        # Calculate Y limits
        def_ylims = [nonnan.min() - 0.1 * abs(nonnan.min()), 1.1 * nonnan.max()]
        if ylims is not None:
            if ylims[0] is not None:
                def_ylims[0] = min([def_ylims[0], ylims[0]])
            if ylims[1] is not None:
                def_ylims[1] = max([def_ylims[1], ylims[1]])

        # Add space for plot title and mean/SD annotation
        def_ylims[0] -= 0.1 * (def_ylims[1] - def_ylims[0])

        ax_ts.set_ylim(def_ylims)

        # Annotate stats
        maxv = nonnan.max()
        mean = nonnan.mean()
        stdv = nonnan.std()
        p95 = np.percentile(nonnan, 95.0)
    else:
        maxv = 0
        mean = 0
        stdv = 0
        p95 = 0

    stats_label = (r'max: {max:.3f}{units} $\bullet$ mean: {mean:.3f}{units} '
                   r'$\bullet$ $\sigma$: {sigma:.3f}').format(
        max=maxv, mean=mean, units=units or '', sigma=stdv)
    ax_ts.annotate(
        stats_label, xy=(0.98, 0.7), xycoords='axes fraction',
        xytext=(0, 0), textcoords='offset points',
        va='center', ha='right', color=color, size=4,
        bbox={'boxstyle': 'round', 'fc': 'w', 'ec': 'none', 'color': 'none',
              'lw': 0, 'alpha': 0.8}
    )

    # Annotate percentile 95
    ax_ts.plot((0, ntsteps - 1), [p95] * 2, linewidth=.1, color='lightgray')
    ax_ts.annotate(
        '%.2f' % p95, xy=(0, p95), xytext=(-1, 0),
        textcoords='offset points', va='center', ha='right',
        color='lightgray', size=3)

    if cutoff is None:
        cutoff = []

    for i, thr in enumerate(cutoff):
        ax_ts.plot((0, ntsteps - 1), [thr] * 2,
                   linewidth=.2, color='dimgray')

        ax_ts.annotate(
            '%.2f' % thr, xy=(0, thr), xytext=(-1, 0),
            textcoords='offset points', va='center', ha='right',
            color='dimgray', size=3)

    ax_ts.plot(tseries, color=color, linewidth=.8)
    ax_ts.set_xlim((0, ntsteps - 1))

    if gs_dist is not None:
        ax_dist = plt.subplot(gs_dist)
        sns.distplot(tseries, vertical=True, ax=ax_dist)
        ax_dist.set_xlabel('Timesteps')
        ax_dist.set_ylim(ax_ts.get_ylim())
        ax_dist.set_yticklabels([])

        return [ax_ts, ax_dist], gs
    return ax_ts, gs

# Modified from: https://github.com/PennBBL/qsiprep/blob/master/qsiprep/interfaces/niworkflows.py
def plot_dMRI_confounds_carpet(confounds_file,sliceqc_file,mask_nii_path,output_image):

    sns.set_style("whitegrid")
    sns.set_context("paper", font_scale=0.8)

    figure = plt.gcf()

    to_plot = [
        "bval", 
        "eddy_movement_rms_relative_to_first", 
        "eddy_movement_rms_relative_to_previous",
        "eddy_restricted_movement_rms_relative_to_first",
        "eddy_restricted_movement_rms_relative_to_previous"
    ]

    confounds = pd.read_csv(confounds_file,sep="\t")
    confound_names = [p for p in to_plot if p in confounds.columns]
    nconfounds = len(confound_names)
    nrows = 1 + nconfounds

    # Create grid
    grid = mgs.GridSpec(nrows, 1, wspace=0.0, hspace=0.05,
                        height_ratios=[1] * (nrows - 1) + [5])

    grid_id = 0
    palette = color_palette("husl", nconfounds)

    for i, name in enumerate(confound_names):
        tseries = confounds[name]
        confoundplot(tseries, grid[grid_id], color=palette[i], name=name)
        grid_id += 1

    # Create grid
    grid = mgs.GridSpec(nrows, 1, wspace=0.0, hspace=0.05,
                        height_ratios=[1] * (nrows - 1) + [5])
    
    # Load the info from eddy
    slice_scores = np.loadtxt(sliceqc_file, skiprows=1).T
    # Get the slice counts
    mask_img = nb.load(mask_nii_path)
    mask = mask_img.get_fdata() > 0

    masked_slices = (mask * np.arange(mask_img.shape[2])[np.newaxis, np.newaxis, :]
                        ).astype(np.int)
    slice_nums, slice_counts = np.unique(masked_slices[mask], return_counts=True)
    
    plot_sliceqc(slice_scores,slice_counts,subplot=grid[-1])
    figure.savefig(output_image, bbox_inches='tight')
    plt.close(figure)

# Modified from: https://github.com/PennBBL/qsiprep/blob/master/qsiprep/interfaces/niworkflows.py
def plot_gradients(bvals, orig_bvecs, source_filenums, output_fname, final_bvecs=None,
                   frames=60):
    qrads = np.sqrt(bvals)
    qvecs = (qrads[:, np.newaxis] * orig_bvecs)
    qx, qy, qz = qvecs.T
    maxvals = qvecs.max(0)
    minvals = qvecs.min(0)
    color_list = ['b','k','g','y','m','c']
    for i in range(0,len(np.unique(source_filenums))):
        source_filenums = np.where(source_filenums==i,color_list[i],source_filenums)
    def add_lines(ax):
        labels = ['L', 'P', 'S']
        for axnum in range(3):
            minvec = np.zeros(3)
            maxvec = np.zeros(3)
            minvec[axnum] = minvals[axnum]
            maxvec[axnum] = maxvals[axnum]
            x, y, z = np.column_stack([minvec, maxvec])
            ax.plot(x, y, z, color="k")
            txt_pos = maxvec + 5
            ax.text(txt_pos[0], txt_pos[1], txt_pos[2], labels[axnum], size=8,
                    zorder=1, color='k')

    if final_bvecs is not None:
        fqx, fqy, fqz = (qrads[:, np.newaxis] * final_bvecs).T
        fig, axes = plt.subplots(nrows=1, ncols=2, figsize=(10, 5),
                                 subplot_kw={"aspect": "equal", "projection": "3d"})
        orig_ax = axes[0]
        final_ax = axes[1]
        axes_list = [orig_ax, final_ax]
        final_ax.scatter(fqx, fqy, fqz, c=source_filenums, marker="+")
        orig_ax.scatter(qx, qy, qz, c=source_filenums, marker="+")
        final_ax.axis('off')
        add_lines(final_ax)
        final_ax.set_title('After Preprocessing')
    else:
        fig, orig_ax = plt.subplots(nrows=1, ncols=1, figsize=(10, 5),
                                    subplot_kw={"aspect": "equal", "projection": "3d"})
        axes_list = [orig_ax]
        orig_ax.scatter(qx, qy, qz, c=source_filenums, marker="+")
    orig_ax.axis('off')
    orig_ax.set_title("Original Scheme")
    add_lines(orig_ax)
    # Animate rotating the axes
    rotate_amount = np.ones(frames) * 180 / frames
    stay_put = np.zeros_like(rotate_amount)
    rotate_azim = np.concatenate([rotate_amount, stay_put, -rotate_amount, stay_put])
    rotate_elev = np.concatenate([stay_put, rotate_amount, stay_put, -rotate_amount])
    plt.tight_layout()

    def rotate(i):
        for ax in axes_list:
            ax.azim += rotate_azim[i]
            ax.elev += rotate_elev[i]
        return tuple(axes_list)

    anim = animation.FuncAnimation(fig, rotate, frames=frames*4,
                                   interval=20, blit=False)
    anim.save(output_fname, writer='imagemagick', fps=32)

    plt.close(fig)
    fig = None

if __name__ == "__main__":
    print("File should not be ran as a stand alone.")