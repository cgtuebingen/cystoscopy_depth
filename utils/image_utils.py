import numpy as np
import torch
from torch import nn
from torchvision.transforms import Compose, Normalize
import matplotlib.pyplot as plt
import seaborn as sns
import os
from scipy.interpolate import LinearNDInterpolator


def create_circular_mask(h, w, center=None, radius=None):
    if center is None:  # use the middle of the image
        center = (int(w / 2), int(h / 2))
    if radius is None:  # use the smallest distance between the center and image walls
        radius = min(center[0], center[1], w - center[0], h - center[1])

    Y, X = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)

    mask = dist_from_center <= radius
    mask = torch.tensor(mask) == False
    return mask


def lin_interp(shape, xyd):
    # taken from https://github.com/hunse/kitti
    k, m, n = shape
    ij, d = xyd[:, 1::-1], xyd[:, 2]
    f = LinearNDInterpolator(ij, d, fill_value=0)
    J, I = np.meshgrid(np.arange(n), np.arange(m))
    IJ = np.vstack([I.flatten(), J.flatten()]).T
    disparity = f(IJ).reshape(shape)
    return disparity


def set_bn_eval(m):
    if isinstance(m, nn.modules.batchnorm._BatchNorm):
        m.eval()


def invTrans():
    return Compose([Normalize(mean=[0., 0., 0.], std=[1 / 0.229, 1 / 0.224, 1 / 0.225]),
                    Normalize(mean=[-0.485, -0.456, -0.406], std=[1., 1., 1.]), ])


def generate_heatmap_fig(img_tensors, labels, centers=None, minmax=[], align_scales=False, colorbars=None):
    trans = invTrans()
    # width of images
    ratios = []
    imgs = []
    calculate_minmax = len(minmax) == 0
    if centers == None:
        centers = [None for _ in range(len(img_tensors))]

    g_vmax = 0
    for idx, tensor_img in enumerate(img_tensors):
        vmax = -np.inf
        vmin = np.inf
        tensor_squeezed = torch.squeeze(tensor_img)
        if tensor_squeezed.ndim == 2:
            img = tensor_img.cpu().detach().numpy()
            img = np.squeeze(img)  # remove first dimension from 1xNxM
            if colorbars is not None and colorbars[idx] == False:
                ratios.append(1)
            else:
                ratios.append(1.25)
            # initialize vmin if not set
            # add vmin if the image is not centered
            if centers[idx] is None:
                vmin = np.min(np.append(img.flatten(), vmin))
                vmax = np.max(np.append(img.flatten(), vmax))
                g_vmax = max(vmax, g_vmax)

        # rgb img
        elif tensor_squeezed.ndim == 3:
            tensor_squeezed = trans(tensor_squeezed)
            img = tensor_squeezed.cpu().detach().numpy()
            ratios.append(1)  # move color channel dimension to end
            img = np.moveaxis(img, 0, 2)
        else:
            raise Exception("Tried to plot image with dims!=2 && dims!=3")
        if calculate_minmax:
            minmax.append((vmin, vmax))
        imgs.append(img)

    width = np.sum(5 * ratios)
    fig, axs = plt.subplots(ncols=len(ratios), figsize=(width, 6), gridspec_kw={'width_ratios': ratios}, num=1)
    for idx, data in enumerate(zip(imgs, minmax, centers)):
        img, minmax, center = data
        axs[idx].set_title(labels[idx])
        kwargs = {}
        if img.ndim == 2:
            shrink = .7
            if center is not None:
                vmin, vmax = (None, None)
                cmap = "coolwarm"
            # prediction scale should start at 1 regardless of the task if the center is not at 0/modified
            else:
                if align_scales:
                    vmin = 0
                    vmax = g_vmax
                else:
                    vmin, vmax = minmax
                    vmin = np.clip(vmin, 0, None)
                    vmax = np.clip(vmax, 0, None)
                cmap = "viridis"
            try:
                if colorbars is not None:
                    kwargs["cbar"] = colorbars[idx]
                    kwargs["cbar_kws"] = {"shrink": shrink, "pad": 0.15}

                sns.heatmap(img, ax=axs[idx], square=True, xticklabels=False, yticklabels=False, center=center,
                            cmap=cmap, vmin=vmin, vmax=vmax, **kwargs)
            except:
                print("Could not plot, skipping")
        else:
            axs[idx].imshow(img)
            axs[idx].set_axis_off()

    plt.tight_layout(w_pad=0.5, h_pad=0)
    return fig


# hacky method to generate the final imgs for the thesis
def generate_final_imgs(img_tensors, labels, centers=None, minmax=[], align_scales=False, colorbars=None,
                        savefigs=False, figname=""):
    trans = invTrans()
    # width of images
    ratios = []
    imgs = []
    calculate_minmax = len(minmax) == 0
    if centers == None:
        centers = [None for _ in range(len(img_tensors))]

    g_vmax = 0
    for idx, tensor_img in enumerate(img_tensors):
        vmax = -np.inf
        vmin = np.inf
        tensor_squeezed = torch.squeeze(tensor_img)
        if tensor_squeezed.ndim == 2:
            img = tensor_img.cpu().detach().numpy()
            img = np.squeeze(img)  # remove first dimension from 1xNxM
            if colorbars is not None and colorbars[idx] == False:
                ratios.append(1)
            else:
                ratios.append(1.25)
            # initialize vmin if not set
            # add vmin if the image is not centered
            if centers[idx] is None:
                vmin = np.min(np.append(img.flatten(), vmin))
                vmax = np.max(np.append(img.flatten(), vmax))
                g_vmax = max(vmax, g_vmax)

        # rgb img
        elif tensor_squeezed.ndim == 3:
            tensor_squeezed = trans(tensor_squeezed)
            img = tensor_squeezed.cpu().detach().numpy()
            ratios.append(1)  # move color channel dimension to end
            img = np.moveaxis(img, 0, 2)
        else:
            raise Exception("Tried to plot image with dims!=2 && dims!=3")
        if calculate_minmax:
            minmax.append((vmin, vmax))
        imgs.append(img)

    width = np.sum(5 * ratios)
    fig, axs = plt.subplots(ncols=len(ratios), figsize=(width, 6), gridspec_kw={'width_ratios': ratios}, num=1)
    img_folder = "kitti"
    if figname:
        fig_folder = f'../datasets/final_imgs/{img_folder}/{figname}'
        os.makedirs(fig_folder, exist_ok=True)
    for idx, data in enumerate(zip(imgs, minmax, centers)):
        img, minmax, center = data
        axs[idx].set_title(labels[idx])
        kwargs = {}
        if img.ndim == 2:
            shrink = .7
            if center is not None:
                vmin, vmax = (None, None)
                cmap = "coolwarm"
            # prediction scale should start at 1 regardless of the task if the center is not at 0/modified
            else:
                if align_scales:
                    vmin = 0
                    vmax = g_vmax
                else:
                    vmin, vmax = minmax
                    vmin = np.clip(vmin, 0, None)
                    vmax = np.clip(vmax, 0, None)
                cmap = "viridis"
            try:
                if colorbars is not None:
                    cbar_enabled = colorbars[idx]

                sns.heatmap(img, ax=axs[idx], square=True, xticklabels=False, yticklabels=False, cbar=cbar_enabled,
                            cbar_kws={"shrink": shrink}, center=center, cmap=cmap, vmin=vmin, vmax=vmax, **kwargs)
                if savefigs:
                    fig2 = plt.figure(2)
                    plt.axes()
                    sns.heatmap(img, ax=fig2.axes[0], square=True, xticklabels=False, yticklabels=False, cbar=None,
                                center=center, cmap=cmap, vmin=vmin, vmax=vmax, **kwargs)
                    plt.savefig("../datasets/final_imgs/{}/{}/{}.png".format(img_folder, figname, idx),
                                bbox_inches="tight", pad_inches=0)
                    plt.close()
            except:
                print("Could not plot, skipping")
        else:
            axs[idx].imshow(img)
            axs[idx].set_axis_off()
            if savefigs:
                fig2 = plt.figure(2)
                plt.axes()
                fig2.axes[0].imshow(img)
                fig2.axes[0].set_axis_off()
                plt.savefig("../datasets/final_imgs/{}/{}/{}.png".format(img_folder, figname, idx), bbox_inches="tight",
                            pad_inches=0)
                plt.close()
    plt.tight_layout(w_pad=0.5, h_pad=0)
    if figname:
        plt.savefig("../datasets/final_imgs/{}/{}/full.png".format(img_folder, figname), bbox_inches="tight",
                    pad_inches=0)
    return fig
